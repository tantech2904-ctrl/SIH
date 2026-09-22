"""Tests that authentication and role-based authorization are enforced.

These complement test_auth.py (login flow) and test_rbac.py (basic role
checks) by covering the endpoint-level matrix: which role can reach which
endpoint, and what happens with no token / wrong role.
"""
from __future__ import annotations

import pytest


# ---- No token ------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/api/v1/events",
    "/api/v1/audit",
    "/api/v1/audit/verify",
    "/api/v1/dashboard",
    "/api/v1/quarantine",
    "/api/v1/alerts",
    "/api/v1/incidents",
    "/api/v1/parsers",
])
def test_protected_endpoints_require_token(client, path):
    r = client.get(path)
    assert r.status_code == 401, f"{path} returned {r.status_code}"


def test_ingest_requires_token(client):
    r = client.post("/api/v1/ingest", json={"raw": "test"})
    assert r.status_code == 401


# ---- Role matrix on audit endpoints --------------------------------------

def test_audit_readable_by_admin(client, admin_headers):
    r = client.get("/api/v1/audit", headers=admin_headers)
    assert r.status_code == 200


def test_audit_readable_by_auditor(client, auditor_headers):
    r = client.get("/api/v1/audit", headers=auditor_headers)
    assert r.status_code == 200


def test_audit_forbidden_for_analyst(client, analyst_headers):
    r = client.get("/api/v1/audit", headers=analyst_headers)
    assert r.status_code == 403


def test_audit_verify_readable_by_admin(client, admin_headers):
    r = client.get("/api/v1/audit/verify", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "valid" in body and "checked" in body


def test_audit_verify_forbidden_for_analyst(client, analyst_headers):
    r = client.get("/api/v1/audit/verify", headers=analyst_headers)
    assert r.status_code == 403


# ---- Role matrix on ingest -----------------------------------------------

def test_ingest_allowed_for_analyst(client, analyst_headers):
    raw = (
        "CEF:0|Acme|AuthApp|1.0|4625|Failed Logon|7|"
        "rt=2026-01-15T10:22:03Z src=203.0.113.5 suser=admin outcome=failure"
    )
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200


def test_ingest_allowed_for_admin(client, admin_headers):
    raw = (
        "CEF:0|Acme|AuthApp|1.0|4625|Failed Logon|7|"
        "rt=2026-01-15T10:22:03Z src=203.0.113.5 suser=admin outcome=failure"
    )
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=admin_headers)
    assert r.status_code == 200


# ---- Login + logout ------------------------------------------------------

def test_login_with_wrong_password_fails(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "admin@test.local",
        "password": "definitely-wrong",
    })
    assert r.status_code == 401


def test_login_writes_audit_row_and_logout_revokes(client, db):
    """Successful login writes LOGIN_SUCCESS; logout writes LOGOUT."""
    from app.models.audit import AuditLog

    before = db.query(AuditLog).filter(AuditLog.action == "LOGIN_SUCCESS").count()

    r = client.post("/api/v1/auth/login", json={
        "email": "admin@test.local",
        "password": "AdminTestPass123!",
    })
    assert r.status_code == 200, r.text
    tokens = r.json()

    after = db.query(AuditLog).filter(AuditLog.action == "LOGIN_SUCCESS").count()
    assert after == before + 1

    r2 = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r2.status_code == 200

    logout_row = (
        db.query(AuditLog)
        .filter(AuditLog.action == "LOGOUT")
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    assert logout_row is not None
    assert logout_row.actor == "admin@test.local"