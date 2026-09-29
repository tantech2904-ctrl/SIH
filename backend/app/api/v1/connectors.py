"""Connector heartbeat + listing + config endpoints.

POST /connectors/heartbeat              — connector sends every 60s
GET  /connectors                        — frontend lists all known connectors
GET  /connectors/{id}/config            — connector polls for desired state
POST /connectors/{id}/config            — UI sets desired state
"""

import io
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.connector import Connector
from app.models.user import User
from app.schemas.connector import (
    HeartbeatRequest, HeartbeatResponse,
    ConnectorItem, ConnectorList,
    ConnectorConfig, ConnectorConfigUpdate,
)
from app.services.audit_service import record_audit

router = APIRouter()

ONLINE_THRESHOLD_S = 180      # 3 × default heartbeat interval
STALE_THRESHOLD_S = 900       # 15 minutes


def _status_for(last_heartbeat: datetime) -> str:
    now = datetime.now(timezone.utc)
    if last_heartbeat.tzinfo is None:
        last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)
    age = (now - last_heartbeat).total_seconds()
    if age <= ONLINE_THRESHOLD_S:
        return "online"
    if age <= STALE_THRESHOLD_S:
        return "stale"
    return "offline"


@router.post("/heartbeat", response_model=HeartbeatResponse)
@limiter.limit(settings.RATE_LIMIT_INGEST)
def heartbeat(
    request: Request,
    body: HeartbeatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    cid = body.connector_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    row = db.query(Connector).filter(Connector.connector_id == cid).first()
    if row is None:
        row = Connector(
            connector_id=cid,
            hostname=body.hostname,
            os=body.os,
            version=body.version,
            adapters=list(body.adapters),
            available_adapters=list(body.available_adapters),
            first_seen=now,
            last_heartbeat=now,
            last_event_at=body.last_event_at,
            events_total=body.events_total,
        )
        db.add(row)
    else:
        row.hostname = body.hostname
        row.os = body.os
        row.version = body.version
        row.adapters = list(body.adapters)
        row.available_adapters = list(body.available_adapters)
        row.last_heartbeat = now
        if body.last_event_at is not None:
            row.last_event_at = body.last_event_at
        row.events_total = body.events_total

    db.commit()
    return HeartbeatResponse(connector_id=cid, accepted=True)


@router.get("", response_model=ConnectorList)
def list_connectors(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.query(Connector).order_by(Connector.hostname).all()
    items = [
        ConnectorItem(
            connector_id=r.connector_id,
            hostname=r.hostname,
            os=r.os,
            version=r.version,
            adapters=list(r.adapters or []),
            available_adapters=list(r.available_adapters or []),
            desired_adapters=r.desired_adapters,
            config_poll_interval_s=r.config_poll_interval_s or 30,
            first_seen=r.first_seen,
            last_heartbeat=r.last_heartbeat,
            last_event_at=r.last_event_at,
            events_total=r.events_total or 0,
            status=_status_for(r.last_heartbeat),
        )
        for r in rows
    ]
    return ConnectorList(items=items, total=len(items))


@router.get("/{connector_id}/config", response_model=ConnectorConfig)
def get_connector_config(
    connector_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    """Poller endpoint. Returns the desired adapter state for the connector
    to converge on. `desired_adapters = null` means the connector keeps
    whatever its local config chose (no opinion from the backend yet).
    """
    row = db.query(Connector).filter(Connector.connector_id == connector_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return ConnectorConfig(
        desired_adapters=row.desired_adapters,
        poll_interval_s=row.config_poll_interval_s or 30,
    )


@router.post("/{connector_id}/config", response_model=ConnectorConfig)
def set_connector_config(
    request: Request,
    connector_id: str,
    body: ConnectorConfigUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    row = db.query(Connector).filter(Connector.connector_id == connector_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Connector not found")

    if not row.available_adapters:
        raise HTTPException(
            status_code=409,
            detail="Connector has not reported its available adapters yet. "
                   "Ensure it is running the latest version and try again.",
        )    

    if body.desired_adapters is not None:
        # Validate against what this connector actually reported.
        available = set(row.available_adapters or [])
        unknown = sorted(set(body.desired_adapters) - available)
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Adapters not available on this connector: {unknown}",
            )

    if body.poll_interval_s is not None and body.poll_interval_s < 5:
        raise HTTPException(status_code=400, detail="poll_interval_s must be >= 5")

    previous_state = {
        "desired_adapters": row.desired_adapters,
        "config_poll_interval_s": row.config_poll_interval_s,
    }

    if body.desired_adapters is not None:
        row.desired_adapters = body.desired_adapters
    if body.poll_interval_s is not None:
        row.config_poll_interval_s = body.poll_interval_s

    new_state = {
        "desired_adapters": row.desired_adapters,
        "config_poll_interval_s": row.config_poll_interval_s,
    }
    record_audit(
        db,
        actor=user.email,
        action="CONNECTOR_CONFIG_UPDATE",
        resource="connector",
        resource_id=connector_id,
        source_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        previous_state=previous_state,
        new_state=new_state,
    )
    db.commit()

    return ConnectorConfig(
        desired_adapters=row.desired_adapters,
        poll_interval_s=row.config_poll_interval_s,
    )


# ------------------------------------------------------------------ downloads

def _get_server_url(request: Request) -> str:
    target = request.query_params.get("server_url")
    if target:
        return target.rstrip("/")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        host = f"{request.url.hostname}:{request.url.port}"
    return f"{proto}://{host}".rstrip("/")


def _find_bundle_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[2] / "connector_bundle",
        Path(__file__).resolve().parent.parent / "connector_bundle",
        Path(__file__).resolve().parents[4] / "scripts" / "ulpf-connector",
        Path("/app/app/connector_bundle"),
        Path("/app/scripts/ulpf-connector"),
    ]
    for c in candidates:
        if c.exists() and (c / "connector.py").exists():
            return c
    return candidates[0]


@router.get("/download/script")
def download_connector_script(request: Request, os: str = "windows"):
    """Download single runner script (run_connector.bat, run_connector.sh, or run_connector_mac.sh)."""
    server_url = _get_server_url(request)
    bundle_dir = _find_bundle_dir()
    os_clean = os.lower().strip()

    if os_clean in ("linux", "sh"):
        filename = "run_connector.sh"
        media_type = "text/x-shellscript"
    elif os_clean in ("mac", "macos", "apple"):
        filename = "run_connector_mac.sh"
        media_type = "text/x-shellscript"
    else:
        filename = "run_connector.bat"
        media_type = "application/x-bat"

    file_path = bundle_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Script {filename} not found")

    content = file_path.read_text(encoding="utf-8", errors="replace")
    content = content.replace("http://localhost:8000", server_url)

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/bundle")
def download_connector_bundle(request: Request, os: str = "windows"):
    """Download tailored zip package containing connector agent and runner."""
    server_url = _get_server_url(request)
    bundle_dir = _find_bundle_dir()
    if not bundle_dir.exists():
        raise HTTPException(status_code=404, detail="Connector bundle directory not found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in bundle_dir.rglob("*"):
            if not file.is_file():
                continue
            if "__pycache__" in file.parts or ".pytest_cache" in file.parts or file.suffix == ".pyc":
                continue
            rel_path = file.relative_to(bundle_dir)

            try:
                text_content = file.read_text(encoding="utf-8")
                if file.name.endswith((".json", ".bat", ".sh", ".py")):
                    text_content = text_content.replace("http://localhost:8000", server_url)
                zf.writestr(str(rel_path), text_content)
            except Exception:
                zf.write(file, str(rel_path))

    buf.seek(0)
    target_name = f"ulpf-connector-{os.lower()}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{target_name}"'},
    )


@router.get("/install.sh")
def install_sh(request: Request):
    """One-line curl installer for Linux / macOS."""
    server_url = _get_server_url(request)
    script = f"""#!/usr/bin/env bash
set -e
echo "=== ULPF Remote Connector Installer ==="
INSTALL_DIR="$HOME/.ulpf-connector"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo "[*] Downloading connector bundle from {server_url}..."
curl -fsSL "{server_url}/api/v1/connectors/download/bundle?os=linux" -o bundle.zip
unzip -q -o bundle.zip
rm -f bundle.zip
chmod +x run_connector.sh run_connector_mac.sh 2>/dev/null || true
echo "[*] Launching connector..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    exec ./run_connector_mac.sh
else
    exec ./run_connector.sh
fi
"""
    return PlainTextResponse(script)


@router.get("/install.ps1")
def install_ps1(request: Request):
    """One-line PowerShell installer for Windows."""
    server_url = _get_server_url(request)
    script = f"""# ULPF Windows Connector One-Line Installer
$ProgressPreference = 'SilentlyContinue'
Write-Host "=== ULPF Windows Connector Installer ===" -ForegroundColor Cyan
$installDir = "$HOME\\.ulpf-connector"
if (!(Test-Path $installDir)) {{ New-Item -ItemType Directory -Path $installDir -Force | Out-Null }}
Set-Location $installDir
Write-Host "[*] Downloading connector bundle from {server_url}..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "{server_url}/api/v1/connectors/download/bundle?os=windows" -OutFile "$installDir\\bundle.zip" -UseBasicParsing
Expand-Archive -Path "$installDir\\bundle.zip" -DestinationPath $installDir -Force
Remove-Item "$installDir\\bundle.zip" -Force
Write-Host "[*] Starting ULPF Connector..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c run_connector.bat"
"""
    return PlainTextResponse(script)