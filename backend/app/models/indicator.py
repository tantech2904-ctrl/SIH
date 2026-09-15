from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ThreatIndicator(Base):
    __tablename__ = "threat_indicators"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: __import__("uuid").uuid4().hex)
    indicator: Mapped[str] = mapped_column(String(512), index=True, unique=True)
    indicator_type: Mapped[str] = mapped_column(String(32), index=True)
    threat_level: Mapped[str] = mapped_column(String(16), default="UNKNOWN")
    sources: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    active: Mapped[bool] = mapped_column(Boolean, default=True)