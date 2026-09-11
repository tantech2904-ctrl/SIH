
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_analyst
from app.db.session import get_db
from app.models.alert import Alert
from app.models.incident import Incident
from app.models.user import User
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("")
def list_incidents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = None,
    severity: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
):
    q = db.query(Incident)
    if status:
        q = q.filter(Incident.status == status.upper())
    if severity:
        q = q.filter(Incident.severity == severity.upper())
    total = q.count()
    rows = q.order_by(desc(Incident.created_at)).offset((page - 1) * size).limit(size).all()
    return {
        "total": total, "page": page, "size": size,
        "items": [_dict(r) for r in rows],
    }


@router.get("/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    r = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _dict(r)


@router.post("", status_code=201)
def create_incident(
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    inc = Incident(
        incident_id=str(uuid.uuid4()),
        title=body.get("title", "Untitled incident"),
        description=body.get("description", ""),
        severity=body.get("severity", "MEDIUM").upper(),
        status="OPEN",
        source=body.get("source", user.email),
        affected_assets=body.get("affected_assets", []),
        indicators=body.get("indicators", []),
        related_events=body.get("related_events", []),
        mitre=body.get("mitre", []),
        notes=[],
    )
    db.add(inc)
    record_audit(db, actor=user.email, action="INCIDENT_CREATE", resource="incident",
                 resource_id=inc.incident_id, new_state={"title": inc.title})
    db.commit()
    return _dict(inc)


@router.post("/{incident_id}/status")
def set_status(
    incident_id: str,
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    r = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Incident not found")
    status = (body.get("status") or "").upper()
    if status not in ("OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED", "FALSE_POSITIVE"):
        raise HTTPException(status_code=400, detail="Invalid status")
    prev = r.status
    r.status = status
    r.updated_at = datetime.now(timezone.utc)
    record_audit(db, actor=user.email, action="INCIDENT_STATUS", resource="incident",
                 resource_id=incident_id, previous_state={"status": prev}, new_state={"status": status})
    db.commit()
    return _dict(r)


@router.post("/{incident_id}/notes")
def add_note(
    incident_id: str,
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    r = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Incident not found")
    note = {"author": user.email, "text": body.get("text", ""),
            "at": datetime.now(timezone.utc).isoformat()}
    r.notes = list(r.notes or []) + [note]
    r.updated_at = datetime.now(timezone.utc)
    record_audit(db, actor=user.email, action="INCIDENT_NOTE", resource="incident",
                 resource_id=incident_id, new_state={"note": note["text"][:200]})
    db.commit()
    return _dict(r)


def _dict(r: Incident) -> dict:
    return {
        "incident_id": r.incident_id, "title": r.title, "description": r.description,
        "severity": r.severity, "status": r.status,
        "first_seen": r.first_seen.isoformat(), "last_seen": r.last_seen.isoformat(),
        "source": r.source, "affected_assets": r.affected_assets, "indicators": r.indicators,
        "related_events": r.related_events, "mitre": r.mitre, "notes": r.notes,
    }