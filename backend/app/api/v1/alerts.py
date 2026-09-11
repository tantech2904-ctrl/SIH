
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_analyst
from app.db.session import get_db
from app.models.alert import Alert
from app.models.user import User
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("")
def list_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    severity: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
):
    q = db.query(Alert)
    if severity:
        q = q.filter(Alert.severity == severity.upper())
    if status:
        q = q.filter(Alert.status == status.upper())
    total = q.count()
    rows = q.order_by(desc(Alert.created_at)).offset((page - 1) * size).limit(size).all()
    return {
        "total": total, "page": page, "size": size,
        "items": [{
            "alert_id": r.alert_id, "event_id": r.event_id, "rule_id": r.rule_id,
            "rule_name": r.rule_name, "severity": r.severity, "risk_score": r.risk_score,
            "description": r.description, "mitre": r.mitre, "details": r.details,
            "status": r.status, "incident_id": r.incident_id,
            "created_at": r.created_at.isoformat(),
        } for r in rows],
    }


@router.get("/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {
        "alert_id": r.alert_id, "event_id": r.event_id, "rule_id": r.rule_id,
        "rule_name": r.rule_name, "severity": r.severity, "risk_score": r.risk_score,
        "description": r.description, "mitre": r.mitre, "details": r.details,
        "status": r.status, "incident_id": r.incident_id,
        "created_at": r.created_at.isoformat(),
    }


@router.post("/{alert_id}/status")
def update_status(
    alert_id: str,
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    r = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Alert not found")
    new_status = (body.get("status") or "").upper()
    if new_status not in ("OPEN", "ACKNOWLEDGED", "CLOSED", "FALSE_POSITIVE"):
        raise HTTPException(status_code=400, detail="Invalid status")
    prev = r.status
    r.status = new_status
    record_audit(db, actor=user.email, action="ALERT_STATUS", resource="alert",
                 resource_id=alert_id, previous_state={"status": prev}, new_state={"status": new_status})
    db.commit()
    return {"status": r.status}