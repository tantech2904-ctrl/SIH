import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Index, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_actor_ts", "actor", "timestamp"),
        Index("ix_audit_logs_seq", "seq", unique=True),
    )

    # Monotonic chain sequence. Assigned at INSERT time via SQLAlchemy's
    # autoincrement; not settable by application code. This is the
    # authoritative chain order — timestamps are informational only.
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    audit_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    actor: Mapped[str] = mapped_column(String(255), default="system")
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    integrity_hash: Mapped[str] = mapped_column(String(64), default="")
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    # Genesis anchor: exactly one row should carry this flag; inserted by
    # init_db(). Verification treats it as the chain root.
    is_genesis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)