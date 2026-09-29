"""Audit trail service.

Every mutating action writes a row into audit_logs. Each row commits to
the previous row via `prev_hash`, forming a hash chain anchored at a
genesis row (is_genesis=True, prev_hash=""). Verification walks the chain
in `seq` order and reports the first row at which the chain breaks.

HARD INVARIANTS (all three critical):
  1. _payload_for() is the single source of truth for what gets hashed.
     It must ONLY contain values that are stable across a DB round-trip.
     - Do NOT include `timestamp` (SQLite and Postgres round-trip
       datetimes slightly differently).
     - Do NOT include anything derived from object identity or wall-clock
       reads at verify time.
  2. Every column referenced by _payload_for() must be set BEFORE
     _hash_row() is called. Specifically, `audit_id` must be assigned
     explicitly at construction time (str(uuid.uuid4())) — relying on the
     SQLAlchemy column default would leave it None during hashing,
     because Python-side defaults fire at flush time, not at object
     construction.
  3. Chain order is determined by `seq`, a database-assigned monotonic
     integer. Timestamps are informational only. (Previously we used
     (timestamp, audit_id); UUIDs are random, so tie-breaks under
     timestamp collisions could invert insertion order and break the
     chain.)

Changing _payload_for() invalidates every existing row's stored hash —
treat it as a schema break, not a routine refactor.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.models.audit import AuditLog

GENESIS_ACTOR = "system"
GENESIS_ACTION = "GENESIS"
GENESIS_RESOURCE = "audit_chain"


def _hash_row(prev_hash: str, payload: dict) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(json.dumps(payload, default=str, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def _payload_for(row: AuditLog) -> dict:
    """Canonical payload used both at write time and verification time.

    Stability rules:
      - All values must round-trip identically through the DB layer.
      - Every field referenced here must already be set on `row` at the
        moment this is called (see module docstring invariant 2).
      - The timestamp is deliberately excluded — see module docstring.
      - `seq` is included to bind the payload to the row's chain position.
        A row moved to a different position would produce a different
        payload hash and be detected.
    """
    return {
        "audit_id": row.audit_id,
        "seq": row.seq,
        "actor": row.actor,
        "action": row.action,
        "resource": row.resource,
        "resource_id": row.resource_id,
        "previous_state": row.previous_state,
        "new_state": row.new_state,
        "correlation_id": row.correlation_id,
    }


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
    # Select the row with the highest seq — the current tip of the chain.
    prev = (
        db.query(AuditLog)
        .order_by(desc(AuditLog.seq))
        .first()
    )
    prev_hash = prev.integrity_hash if prev else ""

    entry = AuditLog(
        audit_id=str(uuid.uuid4()),  # MUST be set before _payload_for
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
        is_genesis=False,
    )
    db.add(entry)
    db.flush()  # populates entry.seq via the DB autoincrement

    # Now that seq is assigned, compute the integrity hash.
    entry.integrity_hash = _hash_row(prev_hash, _payload_for(entry))
    db.flush()
    return entry


def ensure_genesis(db: Session) -> AuditLog:
    """Insert the genesis row if it doesn't exist. Idempotent."""
    existing = db.query(AuditLog).filter(AuditLog.is_genesis.is_(True)).first()
    if existing:
        return existing

    any_row = db.query(AuditLog).first()
    if any_row is not None:
        raise RuntimeError(
            "Cannot insert genesis row: audit_logs already contains rows. "
            "Manual migration of legacy chains is required."
        )

    entry = AuditLog(
        audit_id=str(uuid.uuid4()),  # MUST be set before _payload_for
        timestamp=datetime.now(timezone.utc),
        actor=GENESIS_ACTOR,
        action=GENESIS_ACTION,
        resource=GENESIS_RESOURCE,
        resource_id=None,
        source_ip=None,
        user_agent=None,
        previous_state=None,
        new_state={"note": "genesis anchor for audit hash chain"},
        correlation_id=None,
        prev_hash="",
        is_genesis=True,
    )
    db.add(entry)
    db.flush()  # populates entry.seq

    entry.integrity_hash = _hash_row("", _payload_for(entry))
    db.flush()
    return entry


def verify_audit_chain(db: Session) -> dict:
    """Walk the audit chain in `seq` order and verify integrity.

    Ordering: seq ASC. This is the authoritative chain order assigned by
    the database at insert time. Timestamps are informational only and
    are not used for ordering.

    Failure classifications (first broken row wins):
      - chain_break_insertion_or_deletion: row.prev_hash does not match
        the previous row's recomputed hash. A row was inserted, deleted,
        or reordered.
      - hash_mismatch: chain link is intact but the row's payload does
        not match its stored integrity_hash.
    """
    rows = (
        db.query(AuditLog)
        .order_by(asc(AuditLog.seq))
        .all()
    )
    chain_length = len(rows)
    verified_at = datetime.now(timezone.utc).isoformat()

    if chain_length == 0:
        return {
            "valid": False,
            "checked": 0,
            "chain_length": 0,
            "first_broken_at": None,
            "broken_audit_id": None,
            "reason": "chain_break_insertion_or_deletion",
            "subreason": "No genesis row found (empty audit log).",
            "detail": "The audit chain has not been initialised.",
            "verified_at": verified_at,
        }

    first = rows[0]
    if not first.is_genesis:
        return {
            "valid": False,
            "checked": 0,
            "chain_length": chain_length,
            "first_broken_at": first.timestamp.isoformat() if first.timestamp else None,
            "broken_audit_id": first.audit_id,
            "reason": "chain_break_insertion_or_deletion",
            "subreason": "First row is not the genesis anchor.",
            "detail": (
                "The genesis row is missing or was replaced. Rows before the "
                "current first row may have been deleted."
            ),
            "verified_at": verified_at,
        }

    expected_genesis_hash = _hash_row("", _payload_for(first))
    if first.prev_hash != "" or first.integrity_hash != expected_genesis_hash:
        return {
            "valid": False,
            "checked": 0,
            "chain_length": chain_length,
            "first_broken_at": first.timestamp.isoformat() if first.timestamp else None,
            "broken_audit_id": first.audit_id,
            "reason": "hash_mismatch",
            "subreason": "Genesis row hash does not match recomputed value.",
            "detail": "The genesis anchor has been tampered with.",
            "verified_at": verified_at,
        }

    prev_row = first
    prev_expected = expected_genesis_hash
    checked = 1

    for row in rows[1:]:
        link_ok = row.prev_hash == prev_expected
        expected_this = _hash_row(row.prev_hash, _payload_for(row))
        payload_ok = row.integrity_hash == expected_this

        if not link_ok:
            return {
                "valid": False,
                "checked": checked,
                "chain_length": chain_length,
                "first_broken_at": row.timestamp.isoformat() if row.timestamp else None,
                "broken_audit_id": row.audit_id,
                "reason": "chain_break_insertion_or_deletion",
                "subreason": (
                    "prev_hash does not match the previous row's recomputed "
                    "hash. A row was inserted, deleted, or altered."
                ),
                "detail": (
                    f"Expected prev_hash={prev_expected[:16]}…, "
                    f"got {row.prev_hash[:16]}…"
                ),
                "verified_at": verified_at,
            }

        if not payload_ok:
            return {
                "valid": False,
                "checked": checked,
                "chain_length": chain_length,
                "first_broken_at": row.timestamp.isoformat() if row.timestamp else None,
                "broken_audit_id": row.audit_id,
                "reason": "hash_mismatch",
                "subreason": "Row payload does not match its stored integrity_hash.",
                "detail": (
                    f"Stored integrity_hash={row.integrity_hash[:16]}…, "
                    f"recomputed={expected_this[:16]}…"
                ),
                "verified_at": verified_at,
            }

        prev_row = row
        prev_expected = expected_this
        checked += 1

    return {
        "valid": True,
        "checked": checked,
        "chain_length": chain_length,
        "first_broken_at": None,
        "broken_audit_id": None,
        "reason": None,
        "subreason": None,
        "detail": f"All {checked} rows verified.",
        "verified_at": verified_at,
    }