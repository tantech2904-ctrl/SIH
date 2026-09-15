from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def _hash_row(prev_hash: str, payload: dict) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(json.dumps(payload, default=str, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def record_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    resource: str,
    resource_id: str | None = None,
    source_ip: str | None = None,
    user_agent: str | None = None,
    previous_state: dict | None = None,
    new_state: dict | None = None,
    correlation_id: str | None = None,
) -> AuditLog:
    prev = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).first()
    prev_hash = prev.integrity_hash if prev else ""

    entry = AuditLog(
        timestamp=datetime.now(timezone.utc),
        actor=actor,
        action=action,
        resource=resource,
        resource_id=resource_id,
        source_ip=source_ip,
        user_agent=user_agent,
        previous_state=previous_state,
        new_state=new_state,
        correlation_id=correlation_id,
        prev_hash=prev_hash,
    )
    payload = {
        "timestamp": entry.timestamp.isoformat(),
        "actor": actor,
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "correlation_id": correlation_id,
    }
    entry.integrity_hash = _hash_row(prev_hash, payload)
    db.add(entry)
    db.flush()
    return entry