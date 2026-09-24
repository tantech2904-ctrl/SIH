"""Tests for editable settings.

Writes go to a temporary .env file, never to the real one. The active
path is controlled via the ULPF_ENV_LIVE env var, which the service
reads on each access.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.settings.editable import EDITABLE_KEY_MAP, MASKED_SENTINEL


@pytest.fixture(autouse=True)
def _temp_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.live"
    env_file.write_text(
        "# comment line\n"
        "LOG_LEVEL=INFO\n"
        "VIRUSTOTAL_API_KEY=\n"
        "SYSLOG_UDP_PORT=5140\n"
        "# another comment\n"
        "JWT_SECRET=donotchange\n"
    )
    monkeypatch.setenv("ULPF_ENV_LIVE", str(env_file))
    # Force the service module to re-resolve its path on next call
    import app.settings.service as svc
    monkeypatch.setattr(svc, "ENV_LIVE_PATH", env_file)
    yield env_file


def test_get_settings_admin_only(client, analyst_headers):
    r = client.get("/api/v1/settings", headers=analyst_headers)
    assert r.status_code == 403


def test_get_settings_returns_groups(client, admin_headers):
    r = client.get("/api/v1/settings", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "groups" in data
    groups = {g["name"] for g in data["groups"]}
    assert "Enrichment" in groups
    assert "Listeners" in groups


def test_get_settings_masks_sensitive(client, admin_headers, _temp_env):
    # Set a sensitive value
    _temp_env.write_text(
        "VIRUSTOTAL_API_KEY=abc-secret-key\n"
        "LOG_LEVEL=INFO\n"
    )
    r = client.get("/api/v1/settings", headers=admin_headers)
    assert r.status_code == 200
    for g in r.json()["groups"]:
        for item in g["items"]:
            if item["key"] == "VIRUSTOTAL_API_KEY":
                assert item["value"] == MASKED_SENTINEL
                assert item["is_set"] is True
                return
    pytest.fail("VIRUSTOTAL_API_KEY not found in response")


def test_get_settings_only_allowlist(client, admin_headers, _temp_env):
    r = client.get("/api/v1/settings", headers=admin_headers)
    keys = set()
    for g in r.json()["groups"]:
        for item in g["items"]:
            keys.add(item["key"])
    # JWT_SECRET is in the env file but must NOT appear
    assert "JWT_SECRET" not in keys
    # But LOG_LEVEL should
    assert "LOG_LEVEL" in keys


def test_post_settings_rejects_unknown_key(client, admin_headers):
    r = client.post(
        "/api/v1/settings",
        json={"updates": {"JWT_SECRET": "hacked", "MADE_UP_KEY": "x"}},
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    rejected_keys = {x["key"] for x in data["rejected"]}
    assert "JWT_SECRET" in rejected_keys
    assert "MADE_UP_KEY" in rejected_keys
    assert data["updated"] == []


def test_post_settings_rejects_type_mismatch(client, admin_headers):
    r = client.post(
        "/api/v1/settings",
        json={"updates": {"SYSLOG_UDP_PORT": "not-a-number"}},
        headers=admin_headers,
    )
    data = r.json()
    assert data["updated"] == []
    assert any(x["key"] == "SYSLOG_UDP_PORT" for x in data["rejected"])


def test_post_settings_preserves_comments(client, admin_headers, _temp_env):
    r = client.post(
        "/api/v1/settings",
        json={"updates": {"LOG_LEVEL": "DEBUG"}},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["updated"] == ["LOG_LEVEL"]
    content = _temp_env.read_text()
    assert "# comment line" in content
    assert "# another comment" in content
    assert "LOG_LEVEL=DEBUG" in content
    assert "JWT_SECRET=donotchange" in content


def test_post_settings_hot_reloads(client, admin_headers):
    from app.core.config import settings
    r = client.post(
        "/api/v1/settings",
        json={"updates": {"LOG_LEVEL": "DEBUG"}},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert settings.LOG_LEVEL == "DEBUG"


def test_post_settings_audit_row(client, admin_headers, db):
    from app.models.audit import AuditLog
    r = client.post(
        "/api/v1/settings",
        json={"updates": {"LOG_LEVEL": "WARNING"}},
        headers=admin_headers,
    )
    assert r.status_code == 200
    row = (
        db.query(AuditLog)
        .filter(AuditLog.action == "SETTINGS_UPDATE")
        .order_by(AuditLog.seq.desc())
        .first()
    )
    assert row is not None
    assert row.resource == "settings"
    assert "LOG_LEVEL" in (row.new_state or {})


def test_masked_sentinel_means_unchanged(client, admin_headers, _temp_env):
    _temp_env.write_text("VIRUSTOTAL_API_KEY=original\n")
    r = client.post(
        "/api/v1/settings",
        json={"updates": {"VIRUSTOTAL_API_KEY": MASKED_SENTINEL}},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["updated"] == []
    assert "VIRUSTOTAL_API_KEY=original" in _temp_env.read_text()


def test_restart_mode_manual_returns_not_restarted(client, admin_headers, monkeypatch):
    monkeypatch.setattr("app.services.restart_service.detect_restart_mode",
                        lambda: "manual")
    r = client.post("/api/v1/settings/restart", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["restarted"] is False
    assert data["mode"] == "manual"


def test_restart_audit_row(client, admin_headers, db, monkeypatch):
    from app.models.audit import AuditLog
    monkeypatch.setattr("app.services.restart_service.detect_restart_mode",
                        lambda: "manual")
    client.post("/api/v1/settings/restart", headers=admin_headers)
    row = (
        db.query(AuditLog)
        .filter(AuditLog.action == "BACKEND_RESTART_REQUESTED")
        .order_by(AuditLog.seq.desc())
        .first()
    )
    assert row is not None