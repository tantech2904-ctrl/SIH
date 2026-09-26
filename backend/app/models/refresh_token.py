"""Refresh token registry — enables rotation with reuse detection.

Every refresh token carries a `jti` (UUID) in its JWT payload. The row
here records issuance, usage, and revocation. On refresh:
  - unknown jti          → reject (forged or pre-3.11.7 token)
  - jti.used_at set      → REUSE DETECTED → revoke all user's tokens
  - jti.revoked_at set   → reject
  - valid                → mark used, issue new token, store new row
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), index=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_jti: Mapped[str | None] = mapped_column(String(36), nullable=True)

    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)