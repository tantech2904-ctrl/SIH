"""Connector registry — hosts running the ULPF cross-platform connector.

Each heartbeat upserts by connector_id (a UUID the connector persists in
~/.ulpf/connector_id). We don't rely on hostname alone because two
connectors can share a host (different configs, different sources).

Adapter state fields:
  - `adapters`             — currently running on the connector (heartbeat-reported)
  - `available_adapters`   — every adapter the connector *could* run on its OS
  - `desired_adapters`     — user-set target from the UI; None = "no opinion"
  - `config_poll_interval_s` — how often the connector polls for desired state
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Connector(Base):
    __tablename__ = "connectors"

    connector_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", server_default="default")
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    os: Mapped[str] = mapped_column(String(32), default="unknown")
    version: Mapped[str] = mapped_column(String(32), default="0.0.0")

    adapters: Mapped[list] = mapped_column(JSON, default=list)             # running
    available_adapters: Mapped[list] = mapped_column(JSON, default=list)   # capabilities
    desired_adapters: Mapped[list | None] = mapped_column(JSON, nullable=True)
    config_poll_interval_s: Mapped[int] = mapped_column(Integer, default=30)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    events_total: Mapped[int] = mapped_column(Integer, default=0)