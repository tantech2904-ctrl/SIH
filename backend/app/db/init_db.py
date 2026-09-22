"""Idempotent bootstrap: roles, users, default detection rules, default parsers."""
from __future__ import annotations

from sqlalchemy import select

from app.core.logging import get_logger
from app.core.security import hash_password
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.user import Role, User, user_roles
from app.models.rule import DetectionRule
from app.models.parser import ParserRegistry
from app.services.audit_service import ensure_genesis

log = get_logger(__name__)


DEFAULT_ROLES = ["ADMIN", "ANALYST", "AUDITOR"]


DEFAULT_RULES = [
    {
        "rule_id": "ULPF-001",
        "name": "Repeated failed authentication",
        "description": "Detects multiple failed authentication events from the same source within a short window.",
        "severity": "MEDIUM",
        "conditions": {"event_type": "authentication", "status": "failure", "threshold": 5, "window_seconds": 300},
        "mitre": ["T1110"],
        "enabled": True,
    },
    {
        "rule_id": "ULPF-002",
        "name": "Successful login after failed attempts",
        "description": "Successful authentication preceded by multiple failures from same source (possible brute-force success).",
        "severity": "HIGH",
        "conditions": {"event_type": "authentication", "status": "success", "preceded_by_failures": 3, "window_seconds": 600},
        "mitre": ["T1078", "T1110"],
        "enabled": True,
    },
    {
        "rule_id": "ULPF-003",
        "name": "Malicious indicator matched",
        "description": "Event contains an indicator flagged malicious by configured enrichment providers.",
        "severity": "HIGH",
        "conditions": {"threat_malicious": True},
        "mitre": ["T1071"],
        "enabled": True,
    },
    {
        "rule_id": "ULPF-004",
        "name": "Port scan signature",
        "description": "Multiple destination ports from the same source in a short window.",
        "severity": "MEDIUM",
        "conditions": {"distinct_ports_threshold": 20, "window_seconds": 120},
        "mitre": ["T1046"],
        "enabled": True,
    },
    {
        "rule_id": "ULPF-005",
        "name": "Privilege escalation indicator",
        "description": "Event categorised as privilege escalation.",
        "severity": "HIGH",
        "conditions": {"event_category": "privilege_escalation"},
        "mitre": ["T1068"],
        "enabled": True,
    },
    {
        "rule_id": "ULPF-006",
        "name": "Unusual destination port",
        "description": "Connection to uncommon service port (not in well-known set).",
        "severity": "LOW",
        "conditions": {"unusual_port": True},
        "mitre": [],
        "enabled": True,
    },
]


def _ensure_roles(db) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name in DEFAULT_ROLES:
        existing = db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
        if not existing:
            existing = Role(name=name, description=f"{name} role")
            db.add(existing)
            db.flush()
        roles[name] = existing
    return roles


def _ensure_user(db, email: str, password: str, roles: list[Role]) -> None:
    existing = db.scalars(select(User).where(User.email == email)).first()
    if existing:
        return
    u = User(email=email, password_hash=hash_password(password), is_active=True, full_name=email.split("@")[0])
    u.roles = roles
    db.add(u)
    db.flush()


def _ensure_rules(db) -> None:
    for r in DEFAULT_RULES:
        existing = db.execute(select(DetectionRule).where(DetectionRule.rule_id == r["rule_id"])).scalar_one_or_none()
        if existing:
            continue
        db.add(DetectionRule(**r))


def _ensure_parser_registry(db) -> None:
    from app.parsers.registry import get_registry
    reg = get_registry()
    for pid, meta in reg.list_metadata().items():
        existing = db.execute(select(ParserRegistry).where(ParserRegistry.parser_id == pid)).scalar_one_or_none()
        if existing:
            continue
        db.add(ParserRegistry(
            parser_id=pid,
            name=meta["name"],
            vendor=meta.get("vendor", "generic"),
            format=meta.get("format", pid),
            version=meta.get("version", "1.0.0"),
            enabled=True,
            metadata_json=meta.get("extra", {}),
        ))


def init_db() -> None:
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        roles = _ensure_roles(db)
        _ensure_user(db, settings.BOOTSTRAP_ADMIN_EMAIL, settings.BOOTSTRAP_ADMIN_PASSWORD, [roles["ADMIN"]])
        _ensure_user(db, settings.BOOTSTRAP_ANALYST_EMAIL, settings.BOOTSTRAP_ANALYST_PASSWORD, [roles["ANALYST"]])
        _ensure_user(db, settings.BOOTSTRAP_AUDITOR_EMAIL, settings.BOOTSTRAP_AUDITOR_PASSWORD, [roles["AUDITOR"]])
        _ensure_rules(db)
        _ensure_parser_registry(db)
        ensure_genesis(db)          
        db.commit()
        log.info("db.init.complete")
    except Exception as e:
        db.rollback()
        log.exception("db.init.failed", error=str(e))
        raise
    finally:
        db.close()



if __name__ == "__main__":
    init_db()