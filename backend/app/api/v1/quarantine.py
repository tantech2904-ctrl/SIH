
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_analyst, require_admin
from app.core.rate_limit import limiter
from app.core.config import settings
from app.db.session import get_db
from app.models.event import Event
from app.models.quarantine import QuarantineEvent
from app.models.user import User
from app.parsers.unknown_analyzer import analyze_unknown
from app.services.audit_service import record_audit
from app.services.replay_service import replay_event
from app.storage.minio_store import get_object_store
from app.services.integrity_service import _key_from_location

router = APIRouter()


@router.get("")
def list_quarantine(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = None,
    reason: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
):
    query = db.query(QuarantineEvent)
    if status:
        query = query.filter(QuarantineEvent.status == status.upper())
    if reason:
        query = query.filter(QuarantineEvent.reason == reason)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(QuarantineEvent.detail.ilike(like), QuarantineEvent.event_id.ilike(like)))
    total = query.count()
    rows = query.order_by(desc(QuarantineEvent.created_at)).offset((page - 1) * size).limit(size).all()
    return {
        "total": total, "page": page, "size": size, "pages": (total + size - 1) // size,
        "items": [{
            "id": r.id, "event_id": r.event_id, "reason": r.reason, "stage": r.stage,
            "detail": r.detail, "detected_format": r.detected_format,
            "detection_confidence": r.detection_confidence,
            "parser_id": r.parser_id, "retry_count": r.retry_count,
            "status": r.status, "created_at": r.created_at.isoformat(),
        } for r in rows],
    }


@router.get("/{quarantine_id}")
def get_quarantine(quarantine_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    r = db.query(QuarantineEvent).filter(QuarantineEvent.id == quarantine_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Quarantine entry not found")
    return {
        "id": r.id, "event_id": r.event_id, "reason": r.reason, "stage": r.stage,
        "detail": r.detail, "detected_format": r.detected_format,
        "detection_confidence": r.detection_confidence,
        "parser_id": r.parser_id, "parser_version": r.parser_version,
        "retry_count": r.retry_count, "errors": r.errors, "analysis": r.analysis,
        "status": r.status, "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


@router.get("/{quarantine_id}/analysis")
def get_analysis(quarantine_id: str, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    r = db.query(QuarantineEvent).filter(QuarantineEvent.id == quarantine_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    # Re-derive current analysis from preserved raw bytes
    ev = db.query(Event).filter(Event.event_id == r.event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event missing")
    from app.models.evidence import RawEvidence
    evidence = db.query(RawEvidence).filter(RawEvidence.event_id == ev.event_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence missing")
    try:
        data = get_object_store().get_bytes(_key_from_location(evidence.storage_location))
        text = data.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    analysis = analyze_unknown(text)
    return {
        "delimiter": analysis.delimiter,
        "field_count": analysis.field_count,
        "notes": analysis.notes,
        "candidates": [{
            "name": c.name, "value": c.value[:200],
            "inferred_types": c.inferred_types,
            "suggested_canonical": c.suggested_canonical,
            "confidence": round(c.confidence, 3),
            "reason": c.reason,
        } for c in analysis.candidates],
    }


@router.post("/{quarantine_id}/approve-mapping")
@limiter.limit(settings.RATE_LIMIT_REPLAY)
def approve_mapping(
    request: Request,
    quarantine_id: str,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    """Approve a set of analyzer-suggested field mappings and register them
    as analyst-approved mappings for the parser of the quarantined event."""
    r = db.query(QuarantineEvent).filter(QuarantineEvent.id == quarantine_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Quarantine not found")
    ev = db.query(Event).filter(Event.event_id == r.event_id).first()
    if not ev or not ev.parser_id:
        raise HTTPException(status_code=400, detail="Event has no parser to attach mappings to")

    mappings = body.get("mappings", [])
    if not mappings:
        raise HTTPException(status_code=400, detail="No mappings provided")

    from app.models.mapping import FieldMapping
    import uuid
    created = []
    for m in mappings:
        of = m.get("original_field")
        cf = m.get("canonical_field")
        conf = float(m.get("confidence", 0.75))
        if not of or not cf:
            continue
        existing = db.query(FieldMapping).filter(
            FieldMapping.parser_id == ev.parser_id,
            FieldMapping.original_field == of,
        ).first()
        if existing:
            existing.canonical_field = cf
            existing.confidence = conf
            existing.mapping_source = "analyst"
            existing.approved = True
            created.append(of)
            continue
        db.add(FieldMapping(
            id=str(uuid.uuid4()),
            parser_id=ev.parser_id,
            parser_version=ev.parser_version or "1.0.0",
            original_field=of,
            canonical_field=cf,
            transformation="direct",
            confidence=conf,
            mapping_source="analyst",
            approved=True,
        ))
        created.append(of)

    record_audit(db, actor=user.email, action="MAPPING_APPROVED", resource="quarantine",
                 resource_id=quarantine_id, new_state={"mappings": created})
    db.commit()
    return {"approved": created}


@router.post("/{quarantine_id}/replay")
@limiter.limit(settings.RATE_LIMIT_REPLAY)
def replay_quarantine(
    request: Request,
    quarantine_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
    parser_id: str | None = Query(None),
):
    r = db.query(QuarantineEvent).filter(QuarantineEvent.id == quarantine_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Quarantine not found")
    ev = db.query(Event).filter(Event.event_id == r.event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event missing")
    run = replay_event(db, event=ev, operator=user.email, parser_id=parser_id, quarantine=r)
    r.retry_count += 1
    record_audit(db, actor=user.email, action="QUARANTINE_REPLAY", resource="quarantine",
                 resource_id=quarantine_id, new_state={"result": run.result, "status": run.new_status})
    db.commit()
    return {"replay_id": run.replay_id, "result": run.result, "new_status": run.new_status, "error": run.error}


@router.delete("/{quarantine_id}")
def delete_quarantine(
    quarantine_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    r = db.query(QuarantineEvent).filter(QuarantineEvent.id == quarantine_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    prev = {"status": r.status, "event_id": r.event_id}
    db.delete(r)
    record_audit(db, actor=user.email, action="QUARANTINE_DELETE", resource="quarantine",
                 resource_id=quarantine_id, previous_state=prev)
    db.commit()
    return {"deleted": True}