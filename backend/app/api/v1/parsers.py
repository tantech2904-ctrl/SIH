
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.parser import ParserRegistry
from app.models.user import User
from app.parsers.registry import get_registry
from app.services.audit_service import record_audit

router = APIRouter()


@router.post("")
def create_parser(body: dict, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    parser_id = (body or {}).get("parser_id") or (body or {}).get("id")
    if not parser_id:
        raise HTTPException(status_code=400, detail="parser_id is required")

    metadata = dict((body or {}).get("metadata") or {})
    row = db.query(ParserRegistry).filter(ParserRegistry.parser_id == parser_id).first()

    if row is None:
        row = ParserRegistry(
            parser_id=parser_id,
            name=(body or {}).get("name") or parser_id,
            vendor=(body or {}).get("vendor") or "generic",
            format=(body or {}).get("format") or "custom",
            version=(body or {}).get("version") or "1.0.0",
            enabled=bool((body or {}).get("enabled", True)),
            metadata_json=metadata,
        )
        db.add(row)
    else:
        row.name = (body or {}).get("name") or row.name
        row.vendor = (body or {}).get("vendor") or row.vendor
        row.format = (body or {}).get("format") or row.format
        row.version = (body or {}).get("version") or row.version
        row.enabled = bool((body or {}).get("enabled", row.enabled))
        row.metadata_json = metadata or row.metadata_json

    record_audit(db, actor=user.email, action="PARSER_CREATE", resource="parser",
                 resource_id=parser_id, new_state={"enabled": row.enabled, "format": row.format})
    db.commit()
    db.refresh(row)
    return {
        "parser_id": row.parser_id,
        "name": row.name,
        "vendor": row.vendor,
        "format": row.format,
        "version": row.version,
        "enabled": row.enabled,
        "metadata": row.metadata_json,
    }


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