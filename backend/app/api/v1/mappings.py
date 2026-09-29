import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_analyst
from app.db.session import get_db
from app.models.mapping import FieldMapping
from app.models.user import User
from app.services.audit_service import record_audit
from app.parsers.registry import get_registry

router = APIRouter()

CORE_PARSER_BUILTIN_MAPPINGS: dict[str, dict[str, str]] = {
    "cef": {
        "src": "source.ip",
        "dst": "destination.ip",
        "spt": "source.port",
        "dpt": "destination.port",
        "suser": "user.name",
        "duser": "target.user.name",
        "act": "action",
        "outcome": "status",
        "request": "extensions.url",
        "cs1": "extensions.custom1",
        "deviceExternalId": "device",
        "proto": "protocol",
    },
    "leef": {
        "src": "source.ip",
        "dst": "destination.ip",
        "srcPort": "source.port",
        "dstPort": "destination.port",
        "usrName": "user.name",
        "identHostName": "source.hostname",
        "fileHash": "extensions.file_hash",
        "proto": "protocol",
        "cat": "category",
        "action": "action",
    },
    "windows_evtx": {
        "TargetUserName": "user.name",
        "SubjectUserName": "actor.user.name",
        "IpAddress": "source.ip",
        "IpPort": "source.port",
        "WorkstationName": "source.hostname",
        "ProcessName": "process.executable",
        "CommandLine": "process.command_line",
        "LogonType": "logon.type",
        "Status": "status",
        "TargetDomainName": "domain.name",
    },
    "windows_eventlog": {
        "TargetUserName": "user.name",
        "SubjectUserName": "actor.user.name",
        "IpAddress": "source.ip",
        "IpPort": "source.port",
        "WorkstationName": "source.hostname",
        "ProcessName": "process.executable",
        "CommandLine": "process.command_line",
        "LogonType": "logon.type",
        "Status": "status",
        "TargetDomainName": "domain.name",
    },
    "rfc5424": {
        "hostname": "source.hostname",
        "app_name": "product",
        "procid": "process.pid",
        "msgid": "event_type",
        "facility": "facility",
        "severity": "severity",
    },
    "json": {
        "src_ip": "source.ip",
        "dest_ip": "destination.ip",
        "user": "user.name",
        "action": "action",
        "status": "status",
        "host": "source.hostname",
    },
    "jsonl": {
        "src_ip": "source.ip",
        "dest_ip": "destination.ip",
        "user": "user.name",
        "action": "action",
        "status": "status",
        "host": "source.hostname",
    },
    "csv": {
        "src_ip": "source.ip",
        "dst_ip": "destination.ip",
        "src_port": "source.port",
        "dst_port": "destination.port",
        "protocol": "protocol",
        "action": "action",
    },
    "xml": {
        "source": "source.hostname",
        "destination": "destination.hostname",
        "user": "user.name",
        "action": "action",
    },
}


def _get_all_builtin_mappings(target_parser_id: str | None = None) -> list[dict]:
    """Retrieve built-in shipped field mappings for core and dynamic plugin parsers."""
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()

    # 1. Core parsers
    for pid, fmap in CORE_PARSER_BUILTIN_MAPPINGS.items():
        if target_parser_id and pid != target_parser_id:
            continue
        for orig, canon in fmap.items():
            seen.add((pid, orig))
            items.append({
                "id": f"builtin:{pid}:{orig}",
                "parser_id": pid,
                "parser_version": "1.0.0",
                "original_field": orig,
                "canonical_field": canon,
                "transformation": "direct",
                "confidence": 1.0,
                "source": "builtin",
                "approved": True,
                "notes": "Shipped default CSE mapping",
                "created_at": "2026-01-01T00:00:00Z",
            })

    # 2. Dynamic plugin parsers (e.g. Cisco ASA, Fortigate, Palo Alto, etc.)
    try:
        reg = get_registry()
        for p in reg.all():
            pid = p.parser_id
            if target_parser_id and pid != target_parser_id:
                continue
            fmap = getattr(p, "field_mappings", None) or {}
            if isinstance(fmap, dict):
                for orig, canon in fmap.items():
                    if (pid, str(orig)) not in seen and isinstance(canon, str):
                        seen.add((pid, str(orig)))
                        items.append({
                            "id": f"builtin:{pid}:{orig}",
                            "parser_id": pid,
                            "parser_version": getattr(p, "version", "1.0.0"),
                            "original_field": str(orig),
                            "canonical_field": str(canon),
                            "transformation": "direct",
                            "confidence": 1.0,
                            "source": "builtin",
                            "approved": True,
                            "notes": f"Built-in {getattr(p, 'vendor', 'generic')} mapping",
                            "created_at": "2026-01-01T00:00:00Z",
                        })
    except Exception:
        pass

    return items


@router.get("")
def list_mappings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    parser_id: str | None = None,
):
    # Query database custom mappings
    q = db.query(FieldMapping)
    if parser_id:
        q = q.filter(FieldMapping.parser_id == parser_id)
    db_rows = q.order_by(FieldMapping.parser_id, FieldMapping.original_field).all()

    # Track which (parser_id, original_field) are customized in DB
    customized_keys = {(r.parser_id, r.original_field) for r in db_rows}

    # Built-in mappings that haven't been overridden
    builtin_items = [
        m for m in _get_all_builtin_mappings(parser_id)
        if (m["parser_id"], m["original_field"]) not in customized_keys
    ]

    db_items = [{
        "id": r.id,
        "parser_id": r.parser_id,
        "parser_version": r.parser_version,
        "original_field": r.original_field,
        "canonical_field": r.canonical_field,
        "transformation": r.transformation,
        "confidence": r.confidence,
        "source": r.mapping_source or "analyst",
        "approved": r.approved,
        "notes": r.notes,
        "created_at": r.created_at.isoformat(),
    } for r in db_rows]

    # Combine custom DB mappings + built-in mappings
    all_items = sorted(db_items + builtin_items, key=lambda x: (x["parser_id"], x["original_field"]))
    return {"items": all_items}


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
def delete_mapping(
    mapping_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    r = db.query(FieldMapping).filter(FieldMapping.id == mapping_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Mapping not found")
    prev = {
        "parser_id": r.parser_id,
        "original_field": r.original_field,
        "canonical_field": r.canonical_field,
    }
    db.delete(r)
    record_audit(db, actor=user.email, action="MAPPING_DELETE", resource="mapping",
                 resource_id=mapping_id, previous_state=prev)
    db.commit()
    return {"deleted": True}