"""Pytest fixtures.

Tests use an in-memory SQLite database and a local object store so they can
run without PostgreSQL, MinIO, or Redis.
"""

import os

# Configure environment BEFORE importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ulpf.db")
os.environ.setdefault("JWT_SECRET", "test-secret-key-must-be-32-chars-long-xx")
os.environ.setdefault("MINIO_ENDPOINT", "")  # force local store
os.environ.setdefault("MINIO_ACCESS_KEY", "")
os.environ.setdefault("MINIO_SECRET_KEY", "")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("GEOIP_ENABLED", "false")
os.environ.setdefault("RDAP_ENABLED", "false")
os.environ.setdefault("DNS_ENABLED", "false")
os.environ.setdefault("BOOTSTRAP_ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "AdminTestPass123!")
os.environ.setdefault("BOOTSTRAP_ANALYST_EMAIL", "analyst@test.local")
os.environ.setdefault("BOOTSTRAP_ANALYST_PASSWORD", "AnalystTestPass123!")
os.environ.setdefault("BOOTSTRAP_AUDITOR_EMAIL", "auditor@test.local")
os.environ.setdefault("BOOTSTRAP_AUDITOR_PASSWORD", "AuditorTestPass123!")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.main import app
from app.models.user import Role, User
from app.db.init_db import init_db


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db() -> Session:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def admin_token() -> str:
    return create_access_token("admin@test.local", ["ADMIN"])


@pytest.fixture()
def analyst_token() -> str:
    return create_access_token("analyst@test.local", ["ANALYST"])


@pytest.fixture()
def auditor_token() -> str:
    return create_access_token("auditor@test.local", ["AUDITOR"])


@pytest.fixture()
def admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def analyst_headers(analyst_token: str) -> dict:
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture()
def auditor_headers(auditor_token: str) -> dict:
    return {"Authorization": f"Bearer {auditor_token}"}

@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the in-memory slowapi limiter between tests so auth-heavy
    suites don't hit the per-minute cap."""
    try:
        from app.core.rate_limit import limiter
        # slowapi exposes reset() on current versions; fall back to the
        # underlying storage if not.
        if hasattr(limiter, "reset"):
            limiter.reset()
        else:
            limiter._storage.reset()
    except Exception:
        pass
    yield

@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    """Give each test a clean settings state.

    - Point the settings service at a per-test temp env file so writes
      during a test never touch the repo-root .env.
    - Point reload_settings() at a path that doesn't exist so it never
      accidentally reads a real .env from the developer's machine.
    - Snapshot the settings singleton before the test and restore it
      after, so mutations don't leak between tests.
    """
    from app.core.config import settings
    from app.settings import service as settings_service

    env_file = tmp_path / "test.env"
    env_live = tmp_path / "test.env.live"

    # Override the module-level constants the settings service reads from.
    monkeypatch.setattr(settings_service, "ENV_LIVE_PATH", env_live, raising=False)
    monkeypatch.setattr(settings_service, "ENV_FALLBACK_PATH", env_file, raising=False)

    # Override the env vars reload_settings() checks.
    monkeypatch.setenv("ULPF_ENV_LIVE", str(env_live))
    monkeypatch.setenv("ULPF_ENV_FILE", str(env_file))

    # Snapshot the singleton.
    snapshot = {k: getattr(settings, k) for k in settings.model_fields}
    yield
    for k, v in snapshot.items():
        try:
            setattr(settings, k, v)
        except Exception:
            pass