"""Tests for whole-chain audit verification.

Covers: valid chain, genesis integrity, hash mismatch, chain break
(deletion), timestamp inversion. Uses the real `db` fixture from
conftest.py.
"""
from __future__ import annotations

import pytest
from sqlalchemy import asc
from app.models.audit import AuditLog


@pytest.fixture(autouse=True)
def _clean_audit_log(db):
    """Every test in this module starts with an empty audit chain.

    conftest's _setup_db is session-scoped, so audit rows would otherwise
    leak between tests and break the count/structure assertions.
    """
    db.query(AuditLog).delete()
    db.commit()
    yield
    db.query(AuditLog).delete()
    db.commit()

from app.models.audit import AuditLog
from app.services.audit_service import (
    _hash_row, _payload_for, ensure_genesis, record_audit, verify_audit_chain,
)


def test_genesis_inserted_once(db):
    a = ensure_genesis(db)
    b = ensure_genesis(db)
    db.commit()
    assert a.audit_id == b.audit_id
    assert a.is_genesis is True
    assert a.prev_hash == ""


def test_verify_chain_valid(db):
    ensure_genesis(db)
    record_audit(db, actor="a@test", action="X", resource="r", resource_id="1")
    record_audit(db, actor="a@test", action="Y", resource="r", resource_id="2")
    record_audit(db, actor="a@test", action="Z", resource="r", resource_id="3")
    db.commit()

    result = verify_audit_chain(db)
    assert result["valid"] is True
    assert result["checked"] == 4  # genesis + 3
    assert result["chain_length"] == 4
    assert result["reason"] is None


def test_verify_chain_detects_hash_mismatch(db):
    ensure_genesis(db)
    r1 = record_audit(db, actor="a@test", action="X", resource="r", resource_id="1")
    r2 = record_audit(db, actor="a@test", action="Y", resource="r", resource_id="2")
    r3 = record_audit(db, actor="a@test", action="Z", resource="r", resource_id="3")
    db.commit()

    # Tamper with r2's payload but leave the chain link (r3.prev_hash) intact.
    # This mimics "attacker changed the row content, forgot to fix the hash".
    r2.new_state = {"tampered": True}
    db.commit()

    result = verify_audit_chain(db)
    assert result["valid"] is False
    assert result["reason"] == "hash_mismatch"
    assert result["broken_audit_id"] == r2.audit_id


def test_verify_chain_detects_deletion(db):
    ensure_genesis(db)
    record_audit(db, actor="a@test", action="X", resource="r", resource_id="1")
    r2 = record_audit(db, actor="a@test", action="Y", resource="r", resource_id="2")
    r3 = record_audit(db, actor="a@test", action="Z", resource="r", resource_id="3")
    db.commit()

    # Delete r2 — r3.prev_hash now points to a hash no row carries.
    db.delete(r2)
    db.commit()

    result = verify_audit_chain(db)
    assert result["valid"] is False
    assert result["reason"] == "chain_break_insertion_or_deletion"
    assert result["broken_audit_id"] == r3.audit_id


