"""STIX/TAXII provider — reads a TAXII 2.1 collection for indicator matches."""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.ssrf import validate_outbound_url
from app.enrichment.base import ProviderResult, ThreatIntelProvider


class STIXTAXIIProvider(ThreatIntelProvider):
    name = "STIX/TAXII"
    indicator_types = ("ip", "domain", "url", "hash")

    def is_configured(self) -> bool:
        return bool(settings.STIX_TAXII_ENABLED and settings.STIX_TAXII_URL)

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        url = settings.STIX_TAXII_URL.rstrip("/") + "/objects/"
        validate_outbound_url(url, require_allowlist=False)
        # Note: STIX/TAXII servers are self-hosted by the operator; we do not
        # require allowlisting here but we still block internal addresses.
        auth = None
        if settings.STIX_TAXII_USER:
            auth = (settings.STIX_TAXII_USER, settings.STIX_TAXII_PASS)
        with httpx.Client(timeout=settings.ENRICHMENT_HTTP_TIMEOUT_SECONDS) as c:
            r = c.get(
                url,
                params={"match[type]": "indicator"},
                headers={"Accept": "application/taxii+json;version=2.1"},
                auth=auth,
            )
        if r.status_code == 404:
            return ProviderResult(self.name, indicator, indicator_type, "OK", {"found": False})
        if r.status_code in (401, 403):
            return ProviderResult(self.name, indicator, indicator_type, "NOT_CONFIGURED", {}, error="auth")
        if r.status_code >= 500:
            return ProviderResult(self.name, indicator, indicator_type, "UNAVAILABLE", {}, error=f"upstream {r.status_code}")
        r.raise_for_status()
        data = r.json() or {}
        objects = data.get("objects", [])
        matches = []
        for o in objects:
            pattern = (o.get("pattern") or "")
            if indicator and indicator in pattern:
                matches.append({"id": o.get("id"), "name": o.get("name"), "pattern": pattern})
        return ProviderResult(self.name, indicator, indicator_type, "OK",
                               {"found": bool(matches), "matches": matches[:10]})