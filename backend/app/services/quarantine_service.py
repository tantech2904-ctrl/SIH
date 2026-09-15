from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.quarantine import QuarantineEvent


def quarantine_event(
    db: Session,
    *,
    event: Event,
    reason: str,
    stage: str,
    detail: str,
    errors: list[str] | None = None,
    analysis: dict | None = None,
) -> QuarantineEvent:
    """Move an event into quarantine. Raw evidence is preserved upstream."""
    event.processing_status = "QUARANTINED"
    event.error_message = detail[:2000] if detail else None
    q = QuarantineEvent(
        event_id=event.event_id,
        reason=reason,
        detail=detail,
        stage=stage,
        detected_format=event.detected_format,
        detection_confidence=event.detection_confidence,
        parser_id=event.parser_id,
        parser_version=event.parser_version,
        retry_count=0,
        errors=errors or [],
        analysis=analysis or {},
        status="OPEN",
    )
    db.add(q)
    db.flush()
    return q