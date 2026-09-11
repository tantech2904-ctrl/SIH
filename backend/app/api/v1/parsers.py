
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.parser import ParserRegistry
from app.models.user import User
from app.parsers.registry import get_registry
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("")
def list_parsers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(ParserRegistry).order_by(ParserRegistry.parser_id).all()
    return {"items": [{
        "parser_id": r.parser_id,
        "name": r.name,
        "vendor": r.vendor,
        "format": r.format,
        "version": r.version,
        "enabled": r.enabled,
        "success_count": r.success_count,
        "failure_count": r.failure_count,
        "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
        "metadata": r.metadata_json,
    } for r in rows]}


@router.get("/{parser_id}")
def get_parser(parser_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.query(ParserRegistry).filter(ParserRegistry.parser_id == parser_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Parser not found")
    p = get_registry().get(parser_id)
    return {
        "parser_id": r.parser_id,
        "name": r.name,
        "vendor": r.vendor,
        "format": r.format,
        "version": r.version,
        "enabled": r.enabled,
        "metadata": r.metadata_json,
        "loaded": p is not None,
    }


@router.post("/{parser_id}/enable")
def enable_parser(parser_id: str, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_admin)):
    r = db.query(ParserRegistry).filter(ParserRegistry.parser_id == parser_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Parser not found")
    prev = r.enabled
    r.enabled = True
    record_audit(db, actor=user.email, action="PARSER_ENABLE", resource="parser",
                 resource_id=parser_id, previous_state={"enabled": prev}, new_state={"enabled": True})
    db.commit()
    return {"enabled": True}


@router.post("/{parser_id}/disable")
def disable_parser(parser_id: str, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_admin)):
    r = db.query(ParserRegistry).filter(ParserRegistry.parser_id == parser_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Parser not found")
    prev = r.enabled
    r.enabled = False
    record_audit(db, actor=user.email, action="PARSER_DISABLE", resource="parser",
                 resource_id=parser_id, previous_state={"enabled": prev}, new_state={"enabled": False})
    db.commit()
    return {"enabled": False}