"""Enrichment orchestrator.

Runs all configured providers against the indicators extracted from a CSE.
Never raises — always returns a dict of results.
"""
from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.enrichment.base import ProviderResult, ThreatIntelProvider
from app.enrichment.abuseipdb import AbuseIPDBProvider
from app.enrichment.cache import get_cached, store
from app.enrichment.circuit_breaker import get_breaker
from app.enrichment.dns_provider import DNSProvider
from app.enrichment.geoip import GeoIPProvider
from app.enrichment.mitre import MITREProvider
from app.enrichment.otx import OTXProvider
from app.enrichment.rdap import RDAPProvider
from app.enrichment.stix_taxii import STIXTAXIIProvider
from app.enrichment.virustotal import VirusTotalProvider

log = get_logger(__name__)


def _default_providers() -> list[ThreatIntelProvider]:
    return [
        VirusTotalProvider(),
        AbuseIPDBProvider(),
        OTXProvider(),
        GeoIPProvider(),
        RDAPProvider(),
        DNSProvider(),
        STIXTAXIIProvider(),
        MITREProvider(),
    ]


def extract_indicators(cse: dict) -> list[tuple[str, str]]:
    """Return list of (indicator, type) pairs from a normalized CSE."""
    out: list[tuple[str, str]] = []
    for path, itype in (
        ("source.ip", "ip"),
        ("destination.ip", "ip"),
        ("extensions.ip", "ip"),
        ("extensions.domain", "domain"),
        ("extensions.url", "url"),
        ("extensions.file_hash", "hash"),
    ):
        v = cse.get(path)
        if v:
            out.append((str(v), itype))
    return out


def enrich_cse(
    db: Session,
    *,
    cse: dict,
    event_id: str | None = None,
    providers: Iterable[ThreatIntelProvider] | None = None,
) -> dict:
    """Enrich a CSE in place. Returns a summary dict attached to cse['enrichment']."""
    providers = list(providers) if providers is not None else _default_providers()
    indicators = extract_indicators(cse)
    summary: dict = {"providers": {}, "indicators": [], "threat_malicious": False,
                     "threat_suspicious": False}

    for indicator, itype in indicators:
        per_indicator: dict = {"indicator": indicator, "type": itype, "results": []}
        for p in providers:
            breaker = get_breaker(p.name)
            if not breaker.allow():
                r = ProviderResult(p.name, indicator, itype, "UNAVAILABLE",
                                    {}, error="circuit breaker open")
                per_indicator["results"].append(r.to_dict())
                continue

            if not p.is_configured():
                r = ProviderResult(p.name, indicator, itype, "NOT_CONFIGURED")
                per_indicator["results"].append(r.to_dict())
                summary["providers"].setdefault(p.name, {"status": "NOT_CONFIGURED", "count": 0})
                continue

            cached = get_cached(db, provider=p.name, indicator=indicator, indicator_type=itype)
            if cached is not None:
                summary["providers"].setdefault(p.name, {"status": cached.status, "count": 0})
                summary["providers"][p.name]["count"] += 1
                per_indicator["results"].append({**cached.to_dict(), "cached": True})
                _update_threat_flags(cached, summary)
                continue

            res = p.safe_lookup(indicator, itype)
            if res.status in ("ERROR", "UNAVAILABLE", "TIMEOUT", "RATE_LIMITED"):
                breaker.record_failure()
            else:
                breaker.record_success()
            try:
                store(db, result=res, event_id=event_id, cache=True)
            except Exception as e:
                log.warning("enrich.cache_store_failed", provider=p.name, error=str(e))
            summary["providers"].setdefault(p.name, {"status": res.status, "count": 0})
            summary["providers"][p.name]["count"] += 1
            per_indicator["results"].append(res.to_dict())
            _update_threat_flags(res, summary)

        summary["indicators"].append(per_indicator)

    cse["enrichment"] = summary
    return summary


def _update_threat_flags(result: ProviderResult, summary: dict) -> None:
    if result.status != "OK":
        return
    r = result.result or {}
    if result.provider == "VirusTotal":
        if (r.get("malicious") or 0) > 0 or (r.get("suspicious") or 0) > 2:
            summary["threat_malicious"] = True
    if result.provider == "AbuseIPDB":
        score = r.get("abuse_confidence_score") or 0
        if score >= 75:
            summary["threat_malicious"] = True
        elif score >= 25:
            summary["threat_suspicious"] = True
    if result.provider == "AlienVault OTX":
        if (r.get("pulses") or 0) > 0:
            summary["threat_suspicious"] = True
    if result.provider == "STIX/TAXII":
        if r.get("found"):
            summary["threat_malicious"] = True