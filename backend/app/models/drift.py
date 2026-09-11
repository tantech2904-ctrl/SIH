from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SchemaDrift(Base):
    __tablename__ = "schema_drift"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: __import__("uuid").uuid4().hex)
    vendor: Mapped[str] = mapped_column(String(128), index=True)
    parser_id: Mapped[str] = mapped_column(String(64), index=True)
    parser_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    expected_field: Mapped[str] = mapped_column(String(128))
    observed_field: Mapped[str] = mapped_column(String(128), index=True)
    suggested_canonical: Mapped[str | None] = mapped_column(String(128), nullable=True)
    affected_events: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(String(512), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sample_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)