import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ATTACKMapping(Base):
    __tablename__ = "attck_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), index=True)
    technique_id: Mapped[str] = mapped_column(String(32), index=True)
    technique_name: Mapped[str] = mapped_column(String(255))
    tactic: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    reason: Mapped[str] = mapped_column(String(512), default="")
    source: Mapped[str] = mapped_column(String(32), default="local_heuristic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)