import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CanonicalEvent(Base):
    __tablename__ = "canonical_events"

    cse_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.event_id", ondelete="CASCADE"), unique=True, index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="unknown", index=True)
    category: Mapped[str] = mapped_column(String(64), default="unknown", index=True)
    severity: Mapped[str] = mapped_column(String(16), default="INFO", index=True)

    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    destination_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    destination_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    destination_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    protocol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    product: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)

    tags: Mapped[list] = mapped_column(JSON, default=list)
    enrichment: Mapped[dict] = mapped_column(JSON, default=dict)
    threat_context: Mapped[dict] = mapped_column(JSON, default=dict)
    detection: Mapped[dict] = mapped_column(JSON, default=dict)
    processing_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    extensions: Mapped[dict] = mapped_column(JSON, default=dict)

    risk_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    risk_factors: Mapped[list] = mapped_column(JSON, default=list)
    validation_status: Mapped[str] = mapped_column(String(16), default="VALID")
    validation_notes: Mapped[list] = mapped_column(JSON, default=list)
    mapping_provenance: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)