"""Enrichment cache backed by the enrichment_results table.

Cache is provider + indicator + indicator_type keyed, with a TTL.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.enrichment.base import ProviderResult
from app.models.enrichment import EnrichmentResult


def get_cached(db: Session, *, provider: str, indicator: str, indicator_type: str) -> ProviderResult | None:
    now = datetime.now(timezone.utc)
    row = (
        db.query(EnrichmentResult)
        .filter(
            EnrichmentResult.provider == provider,
            EnrichmentResult.indicator == indicator,
            EnrichmentResult.indicator_type == indicator_type,
            EnrichmentResult.expires_at > now,
        )
        .order_by(desc(EnrichmentResult.created_at))
        .first()
    )
    if not row:
        return None
    return ProviderResult(
        provider=row.provider, indicator=row.indicator, indicator_type=row.indicator_type,
        status=row.status, result=row.result or {}, error=row.error, latency_ms=row.latency_ms,
    )


def store(
    db: Session, *, result: ProviderResult, event_id: str | None = None, cache: bool = True,
) -> EnrichmentResult:
    expires = None
    if cache and result.status == "OK":
        expires = datetime.now(timezone.utc) + timedelta(hours=settings.ENRICHMENT_CACHE_TTL_HOURS)
    row = EnrichmentResult(
        event_id=event_id,
        indicator=result.indicator,
        indicator_type=result.indicator_type,
        provider=result.provider,
        status=result.status,
        latency_ms=result.latency_ms,
        result=result.result,
        error=result.error,
        cached=False,
        expires_at=expires,
    )
    db.add(row)
    db.flush()
    return row


def purge_expired(db: Session) -> int:
    now = datetime.now(timezone.utc)
    q = db.query(EnrichmentResult).filter(
        and_(EnrichmentResult.expires_at.isnot(None), EnrichmentResult.expires_at <= now)
    )
    n = q.delete(synchronize_session=False)
    db.flush()
    return n