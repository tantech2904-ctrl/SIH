
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_analyst
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.canonical import CanonicalEvent
from app.models.event import Event
from app.models.evidence import RawEvidence
from app.models.processing import ProcessingRun
from app.models.replay import ReplayRun
from app.models.user import User
from app.schemas.event import EventListItem, EventDetail, EventRaw, EventNormalized, EventTimeline
from app.services.audit_service import record_audit
from app.services.integrity_service import verify_integrity
from app.services.replay_service import replay_event
from app.storage.minio_store import get_object_store
from app.services.integrity_service import _key_from_location

router = APIRouter()


@router.get("")
@limiter.limit(settings.RATE_LIMIT_SEARCH)
def list_events(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    q: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    format: Optional[str] = None,
    vendor: Optional[str] = None,
    source_ip: Optional[str] = None,
    destination_ip: Optional[str] = None,
    event_type: Optional[str] = None,
    parser_id: Optional[str] = None,
    min_risk: Optional[int] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
):
    query = db.query(CanonicalEvent).join(Event, Event.event_id == CanonicalEvent.event_id)

    if severity:
        query = query.filter(CanonicalEvent.severity == severity.upper())
    if status:
        query = query.filter(Event.processing_status == status.upper())
    if format:
        query = query.filter(Event.detected_format == format)
    if vendor:
        query = query.filter(CanonicalEvent.vendor.ilike(f"%{vendor}%"))
    if source_ip:
        query = query.filter(CanonicalEvent.source_ip == source_ip)
    if destination_ip:
        query = query.filter(CanonicalEvent.destination_ip == destination_ip)
    if event_type:
        query = query.filter(CanonicalEvent.event_type == event_type)
    if parser_id:
        query = query.filter(Event.parser_id == parser_id)
    if min_risk is not None:
        query = query.filter(CanonicalEvent.risk_score >= min_risk)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            CanonicalEvent.message.ilike(like),
            CanonicalEvent.user_name.ilike(like),
            CanonicalEvent.source_ip.ilike(like),
            CanonicalEvent.destination_ip.ilike(like),
            CanonicalEvent.vendor.ilike(like),
        ))

    total = query.count()
    rows = query.order_by(desc(CanonicalEvent.timestamp)).offset((page - 1) * size).limit(size).all()
    ev_ids = [r.event_id for r in rows]
    events = {e.event_id: e for e in db.query(Event).filter(Event.event_id.in_(ev_ids)).all()} if ev_ids else {}

    items = []
    for r in rows:
        e = events.get(r.event_id)
        items.append(EventListItem(
            event_id=r.event_id,
            timestamp=r.timestamp.isoformat(),
            event_type=r.event_type,
            category=r.category,
            severity=r.severity,
            source_ip=r.source_ip,
            destination_ip=r.destination_ip,
            user_name=r.user_name,
            vendor=r.vendor,
            product=r.product,
            message=(r.message or "")[:300],
            risk_score=r.risk_score,
            processing_status=e.processing_status if e else "UNKNOWN",
            detected_format=e.detected_format if e else None,
            parser_id=e.parser_id if e else None,
        ))
    pages = (total + size - 1) // size if size else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.get("/{event_id}", response_model=EventDetail)
def get_event(event_id: str, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    e = db.query(Event).filter(Event.event_id == event_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    c = db.query(CanonicalEvent).filter(CanonicalEvent.event_id == event_id).first()
    ev = db.query(RawEvidence).filter(RawEvidence.event_id == event_id).first()
    return EventDetail(
        event_id=e.event_id,
        ingestion_id=e.ingestion_id,
        correlation_id=e.correlation_id,
        ingested_at=e.ingested_at.isoformat() if e.ingested_at else None,
        source=e.source,
        source_type=e.source_type,
        filename=e.filename,
        content_type=e.content_type,
        raw_size=e.raw_size,
        detected_format=e.detected_format,
        detection_confidence=e.detection_confidence,
        parser_id=e.parser_id,
        parser_version=e.parser_version,
        processing_status=e.processing_status,
        error_message=e.error_message,
        severity=e.severity,
        risk_score=e.risk_score,
        sha256=ev.sha256 if ev else None,
        canonical=_canonical_dict(c) if c else None,
    )


@router.get("/{event_id}/raw")
def get_raw(event_id: str, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    e = db.query(Event).filter(Event.event_id == event_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    ev = db.query(RawEvidence).filter(RawEvidence.event_id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="No raw evidence")
    try:
        data = get_object_store().get_bytes(_key_from_location(ev.storage_location))
        text = data.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Evidence retrieval failed: {exc}")

    ev.accessed_count += 1
    record_audit(db, actor=user.email, action="EVIDENCE_ACCESS", resource="evidence",
                 resource_id=ev.evidence_id, new_state={"event_id": event_id})
    db.commit()
    return EventRaw(
        event_id=event_id,
        content_type=ev.content_type,
        raw_size=ev.raw_size,
        sha256=ev.sha256,
        content=text,
    )


@router.get("/{event_id}/normalized")
def get_normalized(event_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    c = db.query(CanonicalEvent).filter(CanonicalEvent.event_id == event_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="No canonical event")
    return _canonical_dict(c)


@router.get("/{event_id}/integrity")
def get_integrity(event_id: str, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    ev = db.query(RawEvidence).filter(RawEvidence.event_id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="No evidence")
    result = verify_integrity(db, ev)
    record_audit(db, actor=user.email, action="INTEGRITY_VERIFY", resource="evidence",
                 resource_id=ev.evidence_id, new_state={"status": result["integrity_status"]})
    db.commit()
    return result


@router.get("/{event_id}/timeline")
def get_timeline(event_id: str, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    runs = db.query(ProcessingRun).filter(ProcessingRun.event_id == event_id).order_by(ProcessingRun.started_at).all()
    return EventTimeline(
        event_id=event_id,
        stages=[{
            "stage": r.stage,
            "status": r.status,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_ms": r.duration_ms,
            "component": r.component,
            "error": r.error,
        } for r in runs],
    )


@router.get("/{event_id}/replay-history")
def get_replay_history(event_id: str, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    runs = db.query(ReplayRun).filter(ReplayRun.event_id == event_id).order_by(desc(ReplayRun.created_at)).all()
    return {"items": [{
        "replay_id": r.replay_id,
        "previous_status": r.previous_status,
        "new_status": r.new_status,
        "operator": r.operator,
        "result": r.result,
        "created_at": r.created_at.isoformat(),
        "error": r.error,
    } for r in runs]}


@router.post("/{event_id}/replay")
@limiter.limit(settings.RATE_LIMIT_REPLAY)
def post_replay(
    request: Request,
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
    parser_id: Optional[str] = Query(None),
):
    e = db.query(Event).filter(Event.event_id == event_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if e.processing_status not in ("QUARANTINED", "FAILED", "WARNING", "PROCESSED"):
        raise HTTPException(status_code=400, detail=f"Cannot replay from status {e.processing_status}")

    run = replay_event(db, event=e, operator=user.email, parser_id=parser_id)
    record_audit(db, actor=user.email, action="REPLAY", resource="event",
                 resource_id=event_id, new_state={"result": run.result, "new_status": run.new_status})
    db.commit()
    return {
        "replay_id": run.replay_id,
        "previous_status": run.previous_status,
        "new_status": run.new_status,
        "result": run.result,
        "error": run.error,
    }


def _canonical_dict(c: CanonicalEvent) -> dict:
    return {
        "cse_id": c.cse_id,
        "event_id": c.event_id,
        "timestamp": c.timestamp.isoformat(),
        "event_type": c.event_type,
        "category": c.category,
        "severity": c.severity,
        "source": {"ip": c.source_ip, "port": c.source_port, "hostname": c.source_hostname},
        "destination": {"ip": c.destination_ip, "port": c.destination_port, "hostname": c.destination_hostname},
        "user": {"name": c.user_name},
        "action": c.action,
        "protocol": c.protocol,
        "device": c.device,
        "vendor": c.vendor,
        "product": c.product,
        "message": c.message,
        "status": c.status,
        "raw_reference": c.raw_reference,
        "tags": c.tags,
        "extensions": c.extensions,
        "enrichment": c.enrichment,
        "threat_context": c.threat_context,
        "detection": c.detection,
        "processing_metadata": c.processing_metadata,
        "risk_score": c.risk_score,
        "risk_factors": c.risk_factors,
        "validation_status": c.validation_status,
        "validation_notes": c.validation_notes,
        "mapping_provenance": c.mapping_provenance,
    }