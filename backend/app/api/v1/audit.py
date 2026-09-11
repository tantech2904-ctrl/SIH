from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter()


@router.get("")
def list_audit(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "AUDITOR")),
    actor: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
):
    q = db.query(AuditLog)
    if actor:
        q = q.filter(AuditLog.actor == actor)
    if action:
        q = q.filter(AuditLog.action == action)
    if resource:
        q = q.filter(AuditLog.resource == resource)
    total = q.count()
    rows = q.order_by(desc(AuditLog.timestamp)).offset((page - 1) * size).limit(size).all()
    return {
        "total": total, "page": page, "size": size,
        "items": [{
            "audit_id": r.audit_id, "timestamp": r.timestamp.isoformat(),
            "actor": r.actor, "action": r.action, "resource": r.resource,
            "resource_id": r.resource_id, "source_ip": r.source_ip,
            "correlation_id": r.correlation_id,
            "previous_state": r.previous_state, "new_state": r.new_state,
            "integrity_hash": r.integrity_hash, "prev_hash": r.prev_hash,
        } for r in rows],
    }