import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), index=True)
    stage: Mapped[str] = mapped_column(String(32), index=True)  # INGESTED|PRESERVED|HASHED|DETECTED|PARSED|NORMALIZED|ENRICHED|VALIDATED|ROUTED
    status: Mapped[str] = mapped_column(String(16), default="OK")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    component: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)