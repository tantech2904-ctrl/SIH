from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.ssrf import validate_outbound_url
from app.enrichment.base import ProviderResult, ThreatIntelProvider

BASE = "https://otx.alienvault.com/api/v1/indicators"


class OTXProvider(ThreatIntelProvider):
    name = "AlienVault OTX"
    indicator_types = ("ip", "domain", "url", "hash")

    def is_configured(self) -> bool:
        return bool(settings.OTX_ENABLED and settings.OTX_API_KEY)

    def _path(self, indicator: str, indicator_type: str) -> str:
        if indicator_type == "ip":
            return f"{BASE}/IPv4/{indicator}/general"
        if indicator_type == "domain":
            return f"{BASE}/domain/{indicator}/general"
        if indicator_type == "url":
            return f"{BASE}/url/{indicator}/general"
        return f"{BASE}/file/{indicator}/general"

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        url = self._path(indicator, indicator_type)
        validate_outbound_url(url, require_allowlist=True)
        with httpx.Client(timeout=settings.ENRICHMENT_HTTP_TIMEOUT_SECONDS) as c:
            r = c.get(url, headers={"X-OTX-API-KEY": settings.OTX_API_KEY})
        if r.status_code == 404:
            return ProviderResult(self.name, indicator, indicator_type, "OK", {"found": False})
        if r.status_code == 429:
            return ProviderResult(self.name, indicator, indicator_type, "RATE_LIMITED", {}, error="quota")
        if r.status_code in (401, 403):
            return ProviderResult(self.name, indicator, indicator_type, "NOT_CONFIGURED", {}, error=f"auth {r.status_code}")
        if r.status_code >= 500:
            return ProviderResult(self.name, indicator, indicator_type, "UNAVAILABLE", {}, error=f"upstream {r.status_code}")
        r.raise_for_status()
        data = r.json() or {}
        pulse_info = data.get("pulse_info", {}) or {}
        return ProviderResult(self.name, indicator, indicator_type, "OK", {
            "found": True,
            "pulses": pulse_info.get("count", 0),
            "reputation": data.get("reputation"),
            "tags": (pulse_info.get("tags") or [])[:10],
        })