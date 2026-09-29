from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.quarantine import QuarantineEvent
from app.models.replay import ReplayRun
from app.services.ingest_service import process_existing_event


def replay_event(
    db: Session,
    *,
    event: Event,
    operator: str,
    parser_id: str | None = None,
    quarantine: QuarantineEvent | None = None,
) -> ReplayRun:
    """Deterministic replay: re-runs the pipeline against the preserved raw evidence."""
    previous_status = event.processing_status

    run = ReplayRun(
        replay_id=str(uuid.uuid4()),
        event_id=event.event_id,
        quarantine_id=quarantine.id if quarantine else None,
        parser_id=parser_id or event.parser_id,
        parser_version=event.parser_version,
        previous_status=previous_status,
        new_status="",
        operator=operator,
        result="RUNNING",
    )
    db.add(run)
    db.flush()

    try:
        process_existing_event(db, event=event, force_parser=parser_id)
        run.new_status = event.processing_status
        run.result = "SUCCESS" if event.processing_status in ("PROCESSED", "WARNING") else "FAILED"
        if quarantine and event.processing_status in ("PROCESSED", "WARNING"):
            quarantine.status = "REPLAYED"
    except Exception as e:
        run.new_status = event.processing_status
        run.result = "FAILED"
        run.error = str(e)[:2000]
    finally:
        run.extra = {"finished_at": datetime.now(timezone.utc).isoformat()}
        db.flush()
    return run