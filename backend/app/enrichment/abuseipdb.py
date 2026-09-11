from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.ssrf import validate_outbound_url
from app.enrichment.base import ProviderResult, ThreatIntelProvider

BASE = "https://api.abuseipdb.com/api/v2/check"


class AbuseIPDBProvider(ThreatIntelProvider):
    name = "AbuseIPDB"
    indicator_types = ("ip",)

    def is_configured(self) -> bool:
        return bool(settings.ABUSEIPDB_ENABLED and settings.ABUSEIPDB_API_KEY)

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        validate_outbound_url(BASE, require_allowlist=True)
        with httpx.Client(timeout=settings.ENRICHMENT_HTTP_TIMEOUT_SECONDS) as c:
            r = c.get(
                BASE,
                params={"ipAddress": indicator, "maxAgeInDays": 90},
                headers={"Key": settings.ABUSEIPDB_API_KEY, "Accept": "application/json"},
            )
        if r.status_code == 429:
            return ProviderResult(self.name, indicator, indicator_type, "RATE_LIMITED",
                                   {}, error="quota exhausted")
        if r.status_code in (401, 403):
            return ProviderResult(self.name, indicator, indicator_type, "NOT_CONFIGURED",
                                   {}, error=f"auth {r.status_code}")
        if r.status_code >= 500:
            return ProviderResult(self.name, indicator, indicator_type, "UNAVAILABLE",
                                   {}, error=f"upstream {r.status_code}")
        r.raise_for_status()
        data = (r.json() or {}).get("data", {}) or {}
        return ProviderResult(self.name, indicator, indicator_type, "OK", {
            "abuse_confidence_score": data.get("abuseConfidenceScore"),
            "country_code": data.get("countryCode"),
            "usage_type": data.get("usageType"),
            "isp": data.get("isp"),
            "domain": data.get("domain"),
            "total_reports": data.get("totalReports"),
            "last_reported_at": data.get("lastReportedAt"),
        })