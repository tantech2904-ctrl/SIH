"""Connector heartbeat + listing + config endpoints.

POST /connectors/heartbeat              — connector sends every 60s
GET  /connectors                        — frontend lists all known connectors
GET  /connectors/{id}/config            — connector polls for desired state
POST /connectors/{id}/config            — UI sets desired state
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
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