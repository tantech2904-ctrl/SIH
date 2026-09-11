"""Pytest fixtures.

Tests use an in-memory SQLite database and a local object store so they can
run without PostgreSQL, MinIO, or Redis.
"""
from __future__ import annotations

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