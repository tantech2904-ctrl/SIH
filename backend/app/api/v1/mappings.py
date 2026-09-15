
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_analyst
from app.db.session import get_db
from app.models.mapping import FieldMapping
from app.models.user import User
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("")
def list_mappings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    parser_id: str | None = None,
):
    q = db.query(FieldMapping)
    if parser_id:
        q = q.filter(FieldMapping.parser_id == parser_id)
    rows = q.order_by(FieldMapping.parser_id, FieldMapping.original_field).all()
    return {"items": [{
        "id": r.id, "parser_id": r.parser_id, "parser_version": r.parser_version,
        "original_field": r.original_field, "canonical_field": r.canonical_field,
        "transformation": r.transformation, "confidence": r.confidence,
        "source": r.mapping_source, "approved": r.approved, "notes": r.notes,
        "created_at": r.created_at.isoformat(),
    } for r in rows]}


@router.post("", status_code=201)
def create_mapping(
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    pid = body.get("parser_id")
    of = body.get("original_field")
    cf = body.get("canonical_field")
    if not (pid and of and cf):
        raise HTTPException(status_code=400, detail="parser_id, original_field, canonical_field required")

    existing = db.query(FieldMapping).filter(
        FieldMapping.parser_id == pid, FieldMapping.original_field == of,
    ).first()
    if existing:
        existing.canonical_field = cf
        existing.confidence = float(body.get("confidence", 1.0))
        existing.mapping_source = "analyst"
        existing.approved = True
        row = existing
    else:
        row = FieldMapping(
            id=str(uuid.uuid4()),
            parser_id=pid,
            parser_version=body.get("parser_version", "1.0.0"),
            original_field=of,
            canonical_field=cf,
            transformation=body.get("transformation", "direct"),
            confidence=float(body.get("confidence", 1.0)),
            mapping_source="analyst",
            approved=True,
        )
        db.add(row)
    record_audit(db, actor=user.email, action="MAPPING_UPSERT", resource="mapping",
                 resource_id=f"{pid}:{of}", new_state={"canonical_field": cf})
    db.commit()
    return {"id": row.id}


@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: str, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_analyst)):
    r = db.query(FieldMapping).filter(FieldMapping.id == mapping_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Mapping not found")
    prev = {"parser_id": r.parser_id, "original_field": r.original_field,
            "canonical_field": r.canonical_field}
    db.delete(r)
    record_audit(db, actor=user.email, action="MAPPING_DELETE", resource="mapping",
                 resource_id=mapping_id, previous_state=prev)
    db.commit()
    return {"deleted": True}