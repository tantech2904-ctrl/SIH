"""Simple correlation: group events by shared identifiers within a time window."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.canonical import CanonicalEvent


def correlate_recent(db: Session, *, minutes: int | None = None) -> dict:
    window = minutes or (settings.CORRELATION_WINDOW_SECONDS // 60)
    since = datetime.now(timezone.utc) - timedelta(minutes=window)
    events = db.query(CanonicalEvent).filter(CanonicalEvent.timestamp >= since).all()

    by_source_ip: dict[str, list] = defaultdict(list)
    by_user: dict[str, list] = defaultdict(list)
    by_hostname: dict[str, list] = defaultdict(list)

    for e in events:
        if e.source_ip:
            by_source_ip[e.source_ip].append(e)
        if e.user_name:
            by_user[e.user_name].append(e)
        if e.device:
            by_hostname[e.device].append(e)

    groups = []
    for key, items in by_source_ip.items():
        if len(items) >= 3:
            groups.append(_summarize("source_ip", key, items))
    for key, items in by_user.items():
        if len(items) >= 3:
            groups.append(_summarize("user", key, items))
    for key, items in by_hostname.items():
        if len(items) >= 3:
            groups.append(_summarize("hostname", key, items))

    return {"window_minutes": window, "groups": groups}


def _summarize(kind: str, key: str, items: list[CanonicalEvent]) -> dict:
    severities = [e.severity for e in items if e.severity]
    worst = max(severities, key=_sev_rank) if severities else "INFO"
    return {
        "kind": kind,
        "key": key,
        "count": len(items),
        "worst_severity": worst,
        "max_risk": max((e.risk_score or 0 for e in items), default=0),
        "first_seen": min(e.timestamp for e in items).isoformat(),
        "last_seen": max(e.timestamp for e in items).isoformat(),
        "event_ids": [e.event_id for e in items[:50]],
    }


def _sev_rank(s: str) -> int:
    order = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    return order.index(s.upper()) if s and s.upper() in order else 0