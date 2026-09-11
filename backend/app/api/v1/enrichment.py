
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.enrichment.orchestrator import enrich_cse
from app.models.canonical import CanonicalEvent
from app.models.enrichment import EnrichmentResult
from app.models.user import User

router = APIRouter()


@router.get("/{event_id}")
def get_enrichment(event_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    c = db.query(CanonicalEvent).filter(CanonicalEvent.event_id == event_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Event not found")
    if not c.enrichment:
        # Derive on demand (does not persist)
        cse = {"source.ip": c.source_ip, "destination.ip": c.destination_ip,
               "extensions": c.extensions or {}}
        summary = enrich_cse(db, cse=cse, event_id=event_id)
        db.rollback()  # do not persist results from a read-only route
        return summary
    return c.enrichment


@router.get("/providers/status")
def provider_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.enrichment.orchestrator import _default_providers
    out = []
    for p in _default_providers():
        out.append({"provider": p.name, "configured": p.is_configured(),
                    "indicator_types": list(p.indicator_types)})
    return {"providers": out}