"""GeoIP enrichment.

Uses a locally-provided MaxMind GeoLite2 City database when configured.
If GEOIP_ENABLED is false, or the mmdb file is missing, returns
NOT_CONFIGURED. Private / loopback / link-local IPs are explicitly NOT
geolocated.
"""
from __future__ import annotations

import os

from app.core.config import settings
from app.core.ssrf import classify_ip
from app.enrichment.base import ProviderResult, ThreatIntelProvider


class GeoIPProvider(ThreatIntelProvider):
    name = "GeoIP"
    indicator_types = ("ip",)

    def __init__(self) -> None:
        self._reader = None
        self._load_attempted = False

    def is_configured(self) -> bool:
        if not settings.GEOIP_ENABLED:
            return False
        if not settings.MAXMIND_DB_PATH:
            return False
        return os.path.exists(settings.MAXMIND_DB_PATH)

    def _load(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True
        try:
            import geoip2.database  # type: ignore
            self._reader = geoip2.database.Reader(settings.MAXMIND_DB_PATH)
        except Exception:
            self._reader = None

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        cls = classify_ip(indicator)
        if cls != "PUBLIC":
            return ProviderResult(
                self.name, indicator, indicator_type, "OK",
                {"classification": cls, "geolocated": False,
                 "note": "Non-public IP addresses are not geolocated."},
            )
        self._load()
        if self._reader is None:
            return ProviderResult(self.name, indicator, indicator_type, "UNAVAILABLE",
                                   {}, error="GeoIP database not available")
        try:
            r = self._reader.city(indicator)
        except Exception as e:
            return ProviderResult(self.name, indicator, indicator_type, "ERROR",
                                   {}, error=str(e))
        return ProviderResult(
            self.name, indicator, indicator_type, "OK",
            {
                "classification": "PUBLIC",
                "geolocated": True,
                "approximate": True,
                "country": r.country.iso_code,
                "country_name": r.country.name,
                "region": r.subdivisions.most_specific.name if r.subdivisions else None,
                "city": r.city.name,
                "latitude": r.location.latitude,
                "longitude": r.location.longitude,
                "asn": None,
                "organization": None,
            },
        )