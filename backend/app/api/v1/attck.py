from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.detection.attck_map import list_all
from app.models.attck import ATTACKMapping
from app.models.user import User

router = APIRouter()


@router.get("")
def list_techniques(user: User = Depends(get_current_user)):
    return {"techniques": list_all()}


@router.get("/events/{event_id}")
def event_mappings(event_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    rows = db.query(ATTACKMapping).filter(ATTACKMapping.event_id == event_id).all()
    return {"items": [{
        "technique_id": r.technique_id, "technique_name": r.technique_name,
        "tactic": r.tactic, "confidence": r.confidence, "reason": r.reason, "source": r.source,
    } for r in rows]}