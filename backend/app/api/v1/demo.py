"""
demo.py — One-click demo ingestion endpoint.

Fires all testlab scenarios once per call, returns event count.
No attack simulation — defensive synthetic data only.
Safe to call multiple times (idempotent data, each call adds fresh events).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_analyst
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services.ingest_service import ingest_event, dispatch_after_commit

router = APIRouter()


@router.post("/run")
@limiter.limit("30/minute")
def run_demo(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    """
    Ingest one batch of all synthetic attack scenarios (~11 events).
    Designed to be called repeatedly by the frontend demo animation
    (8 times over 12 seconds) to populate the dashboard live.
    """
    # Local import to avoid circular dependency at module load time
    from app.api.v1.testlab import SCENARIOS  # noqa: PLC0415

    event_ids: list[str] = []
    results: list[dict] = []

    tenant_id = getattr(user, "tenant_id", "default") or "default"
    for name, gen_fn in SCENARIOS.items():
        try:
            raw = gen_fn()
            ev = ingest_event(
                db,
                raw_bytes=raw.encode("utf-8"),
                source=f"demo:{name}",
                source_type="demo",
                filename=f"{name}.log",
                content_type="text/plain",
                tenant_id=tenant_id,
            )
            event_ids.append(ev.event_id)
            results.append({
                "scenario": name,
                "event_id": ev.event_id,
                "status": ev.processing_status,
                "format": ev.detected_format,
            })
        except Exception as exc:  # noqa: BLE001
            results.append({"scenario": name, "error": str(exc)})

    db.commit()
    if event_ids:
        dispatch_after_commit(db, event_ids)

    return {"generated": len(event_ids), "results": results}


@router.get("/status")
def demo_status(user: User = Depends(require_analyst)):
    """Returns available demo scenarios and events per run."""
    from app.api.v1.testlab import SCENARIOS  # noqa: PLC0415
    return {
        "scenarios": list(SCENARIOS.keys()),
        "events_per_run": len(SCENARIOS),
    }
