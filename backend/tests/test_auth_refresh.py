"""Tests for refresh token rotation + reuse detection (Gap 3.11.7).

These tests exercise the full HTTP flow via TestClient so they pin the
contract that the frontend depends on.
"""
from __future__ import annotations

import pytest


ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "AdminTestPass123!"


def _login(client) -> dict:
    r = client.post("/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    assert r.status_code == 200, r.text
    return r.json()


def _refresh(client, refresh_token: str):
    return client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})


def test_login_then_refresh_succeeds(client):
    tok = _login(client)
    assert "access_token" in tok and "refresh_token" in tok

    r = _refresh(client, tok["refresh_token"])
    assert r.status_code == 200, r.text
    new = r.json()
    assert new["access_token"]
    assert new["refresh_token"]
    assert new["refresh_token"] != tok["refresh_token"]


def test_old_refresh_token_rejected_after_rotation(client):
    """After one successful refresh, the OLD token is marked used.
    Replaying it triggers reuse detection and returns 401."""
    tok = _login(client)
    old_refresh = tok["refresh_token"]

    r1 = _refresh(client, old_refresh)
    assert r1.status_code == 200

    r2 = _refresh(client, old_refresh)
    assert r2.status_code == 401
    body = r2.json()
    message = body.get("error", {}).get("message", "") or body.get("detail", "")
    assert "reuse" in message.lower()


def test_reuse_revokes_chain_for_user(client):
    """If a used token is replayed, ALL of the user's active tokens are revoked.
    The newly-issued token from the first refresh must then fail too."""
    tok = _login(client)
    old_refresh = tok["refresh_token"]

    r1 = _refresh(client, old_refresh)
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]

    # Replay the old token → reuse detection → revoke all
    r2 = _refresh(client, old_refresh)
    assert r2.status_code == 401

    # The supposedly-valid new token is now revoked too.
    r3 = _refresh(client, new_refresh)
    assert r3.status_code == 401


def test_logout_revokes_refresh_token(client):
    tok = _login(client)
    refresh = tok["refresh_token"]
    access = tok["access_token"]

    r = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200

    # The revoked token must not be usable.
    r2 = _refresh(client, refresh)
    assert r2.status_code == 401


def test_refresh_without_jti_is_rejected(client):
    """A refresh token whose payload has no `jti` (pre-3.11.7) is rejected
    with a clear message that forces re-login."""
    from app.core.config import settings
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    payload = {
        "sub": ADMIN_EMAIL,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=1)).timestamp()),
        "type": "refresh",
        # intentionally no jti
    }
    legacy_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    r = _refresh(client, legacy_token)
    assert r.status_code == 401
    body = r.json()
    message = body.get("error", {}).get("message", "") or body.get("detail", "")
    assert "re-authentication" in message.lower()
