import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EnrichmentResult(Base):
    __tablename__ = "enrichment_results"
    __table_args__ = (Index("ix_enr_indicator_provider", "indicator", "provider"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    indicator: Mapped[str] = mapped_column(String(512), index=True)
    indicator_type: Mapped[str] = mapped_column(String(32), index=True)  # ip|domain|url|hash|other
    provider: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))  # OK|NOT_CONFIGURED|UNAVAILABLE|TIMEOUT|ERROR|RATE_LIMITED
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cached: Mapped[bool] = mapped_column(default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)