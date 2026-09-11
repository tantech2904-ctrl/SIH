from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FieldMapping(Base):
    __tablename__ = "field_mappings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parser_id: Mapped[str] = mapped_column(String(64), index=True)
    parser_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    original_field: Mapped[str] = mapped_column(String(128))
    canonical_field: Mapped[str] = mapped_column(String(128), index=True)
    transformation: Mapped[str] = mapped_column(String(255), default="direct")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    mapping_source: Mapped[str] = mapped_column(String(32), default="builtin")  # builtin|analyst|analyzer
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)