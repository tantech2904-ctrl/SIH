import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ingestion_id: Mapped[str] = mapped_column(String(36), index=True)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)

    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(64), default="api")
    filename: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(128), default="text/plain")
    raw_size: Mapped[int] = mapped_column(Integer, default=0)

    detected_format: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    parser_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    processing_status: Mapped[str] = mapped_column(String(32), default="RECEIVED", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    extra: Mapped[dict] = mapped_column(JSON, default=dict)