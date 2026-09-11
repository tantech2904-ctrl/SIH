
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_analyst
from app.db.session import get_db
from app.models.drift import SchemaDrift
from app.models.mapping import FieldMapping
from app.models.user import User
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("")
def list_drift(db: Session = Depends(get_db), user: User = Depends(get_current_user),
               approved: bool | None = None):
    q = db.query(SchemaDrift)
    if approved is not None:
        q = q.filter(SchemaDrift.approved.is_(bool(approved)))
    rows = q.order_by(desc(SchemaDrift.created_at)).limit(500).all()
    return {"items": [{
        "id": r.id, "vendor": r.vendor, "parser_id": r.parser_id,
        "expected_field": r.expected_field, "observed_field": r.observed_field,
        "suggested_canonical": r.suggested_canonical,
        "affected_events": r.affected_events, "confidence": r.confidence,
        "reason": r.reason, "approved": r.approved,
        "sample_event_id": r.sample_event_id, "created_at": r.created_at.isoformat(),
    } for r in rows]}


@router.post("/{drift_id}/approve")
def approve_drift(drift_id: str, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_analyst)):
    d = db.query(SchemaDrift).filter(SchemaDrift.id == drift_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Not found")
    if not d.suggested_canonical:
        raise HTTPException(status_code=400, detail="No suggested canonical")
    # Register mapping
    existing = db.query(FieldMapping).filter(
        FieldMapping.parser_id == d.parser_id,
        FieldMapping.original_field == d.observed_field,
    ).first()
    if existing:
        existing.canonical_field = d.suggested_canonical
        existing.mapping_source = "analyst"
        existing.approved = True
        existing.confidence = d.confidence
    else:
        db.add(FieldMapping(
            id=str(uuid.uuid4()),
            parser_id=d.parser_id,
            parser_version=d.parser_version,
            original_field=d.observed_field,
            canonical_field=d.suggested_canonical,
            transformation="direct",
            confidence=d.confidence,
            mapping_source="analyst",
            approved=True,
        ))
    d.approved = True
    from datetime import datetime, timezone
    d.approved_by = user.email
    d.approved_at = datetime.now(timezone.utc)
    record_audit(db, actor=user.email, action="DRIFT_APPROVE", resource="drift",
                 resource_id=drift_id, new_state={"observed_field": d.observed_field,
                                                  "canonical": d.suggested_canonical})
    db.commit()
    return {"approved": True}