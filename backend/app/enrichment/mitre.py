"""MITRE ATT&CK enrichment (local static subset + optional remote technique lookup)."""
from __future__ import annotations

from app.detection.attck_map import ATTACK_TECHNIQUES, map_to_attck  # noqa: F401
from app.enrichment.base import ProviderResult, ThreatIntelProvider


class MITREProvider(ThreatIntelProvider):
    name = "MITRE ATT&CK"
    indicator_types = ("technique",)

    def is_configured(self) -> bool:
        return True

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        tech = map_to_attck(indicator)
        if tech:
            return ProviderResult(self.name, indicator, indicator_type, "OK",
                                   {"found": True, **tech})
        return ProviderResult(self.name, indicator, indicator_type, "OK",
                               {"found": False})