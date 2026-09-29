"""RDAP provider — official registry bootstrap (rdap.org)."""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.ssrf import validate_outbound_url
from app.enrichment.base import ProviderResult, ThreatIntelProvider

BOOTSTRAP = "https://rdap.org"


class RDAPProvider(ThreatIntelProvider):
    name = "RDAP"
    indicator_types = ("ip", "domain")

    def is_configured(self) -> bool:
        return bool(settings.RDAP_ENABLED)

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        if indicator_type == "ip":
            url = f"{BOOTSTRAP}/ip/{indicator}"
        elif indicator_type == "domain":
            url = f"{BOOTSTRAP}/domain/{indicator}"
        else:
            return ProviderResult(self.name, indicator, indicator_type, "OK",
                                   {"skipped": "unsupported_type"})
        validate_outbound_url(url, require_allowlist=True)
        with httpx.Client(timeout=settings.ENRICHMENT_HTTP_TIMEOUT_SECONDS, follow_redirects=True) as c:
            r = c.get(url, headers={"Accept": "application/rdap+json"})
        if r.status_code == 404:
            return ProviderResult(self.name, indicator, indicator_type, "OK", {"found": False})
        if r.status_code == 429:
            return ProviderResult(self.name, indicator, indicator_type, "RATE_LIMITED", {}, error="quota")
        if r.status_code >= 500:
            return ProviderResult(self.name, indicator, indicator_type, "UNAVAILABLE", {}, error=f"upstream {r.status_code}")
        r.raise_for_status()
        data = r.json() or {}
        return ProviderResult(self.name, indicator, indicator_type, "OK", {
            "found": True,
            "handle": data.get("handle"),
            "name": data.get("name"),
            "country": data.get("country"),
            "start_address": data.get("startAddress"),
            "end_address": data.get("endAddress"),
            "status": data.get("status", []),
            "events": data.get("events", [])[:10],
        })