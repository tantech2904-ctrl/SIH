"""VirusTotal provider.

IMPORTANT: We never auto-upload files. By default, file indicators must be
SHA-256 hashes; queries are hash-based. Setting VIRUSTOTAL_UPLOAD_FILES=true
in .env enables file upload, but the core platform does not perform uploads.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.ssrf import validate_outbound_url
from app.enrichment.base import ProviderResult, ThreatIntelProvider


VT_BASE = "https://www.virustotal.com/api/v3"


class VirusTotalProvider(ThreatIntelProvider):
    name = "VirusTotal"
    indicator_types = ("ip", "domain", "url", "hash")

    def is_configured(self) -> bool:
        return bool(settings.VIRUSTOTAL_ENABLED and settings.VIRUSTOTAL_API_KEY)

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        if indicator_type == "ip":
            path = f"/ip_addresses/{indicator}"
        elif indicator_type == "domain":
            path = f"/domains/{indicator}"
        elif indicator_type == "url":
            import base64
            url_id = base64.urlsafe_b64encode(indicator.encode()).rstrip(b"=").decode()
            path = f"/urls/{url_id}"
        elif indicator_type == "hash":
            path = f"/files/{indicator}"
        else:
            return ProviderResult(self.name, indicator, indicator_type, "OK",
                                   {"skipped": "unsupported_type"})

        url = VT_BASE + path
        validate_outbound_url(url, require_allowlist=True)

        with httpx.Client(timeout=settings.ENRICHMENT_HTTP_TIMEOUT_SECONDS) as c:
            r = c.get(url, headers={"x-apikey": settings.VIRUSTOTAL_API_KEY})
        if r.status_code == 404:
            return ProviderResult(self.name, indicator, indicator_type, "OK",
                                   {"found": False})
        if r.status_code == 401:
            return ProviderResult(self.name, indicator, indicator_type, "NOT_CONFIGURED",
                                   {}, error="invalid API key")
        if r.status_code == 403:
            return ProviderResult(self.name, indicator, indicator_type, "UNAVAILABLE",
                                   {}, error="forbidden")
        if r.status_code == 429:
            return ProviderResult(self.name, indicator, indicator_type, "RATE_LIMITED",
                                   {}, error="quota exhausted")
        if r.status_code >= 500:
            return ProviderResult(self.name, indicator, indicator_type, "UNAVAILABLE",
                                   {}, error=f"upstream {r.status_code}")
        r.raise_for_status()
        data = r.json().get("data", {})
        attrs = data.get("attributes", {})
        stats = attrs.get("last_analysis_stats", {}) or {}
        return ProviderResult(
            self.name, indicator, indicator_type, "OK",
            {
                "found": True,
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "harmless": stats.get("harmless", 0),
                "undetected": stats.get("undetected", 0),
                "reputation": attrs.get("reputation"),
                "analysis_date": attrs.get("last_analysis_date"),
                "analysis_stats": stats,
            },
        )