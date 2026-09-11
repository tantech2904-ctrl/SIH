"""Threat-intelligence enrichment provider interface.

Every provider is optional. If a provider is not configured or fails, the
orchestrator records a status (NOT_CONFIGURED / UNAVAILABLE / TIMEOUT /
ERROR / RATE_LIMITED) and the core pipeline continues.

Providers MUST:
- Never raise on network errors (return a result dict with a status).
- Never receive the full raw log — only the minimum indicator needed.
- Respect timeouts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResult:
    provider: str
    indicator: str
    indicator_type: str
    status: str  # OK|NOT_CONFIGURED|UNAVAILABLE|TIMEOUT|ERROR|RATE_LIMITED
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    latency_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "indicator": self.indicator,
            "indicator_type": self.indicator_type,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "latency_ms": self.latency_ms,
        }


class ThreatIntelProvider:
    """Base class. Subclasses set `name`, `indicator_types`, `configured`."""

    name: str = "base"
    indicator_types: tuple[str, ...] = ("ip", "domain", "url", "hash")

    def is_configured(self) -> bool:
        return False

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        """Perform the actual lookup. Override in subclasses."""
        raise NotImplementedError

    def safe_lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        import time
        start = time.perf_counter()
        if not self.is_configured():
            return ProviderResult(
                provider=self.name, indicator=indicator, indicator_type=indicator_type,
                status="NOT_CONFIGURED", latency_ms=0,
            )
        if indicator_type not in self.indicator_types:
            return ProviderResult(
                provider=self.name, indicator=indicator, indicator_type=indicator_type,
                status="OK", result={"skipped": "indicator_type_not_supported"},
                latency_ms=0,
            )
        try:
            res = self.lookup(indicator, indicator_type)
        except TimeoutError:
            return ProviderResult(
                provider=self.name, indicator=indicator, indicator_type=indicator_type,
                status="TIMEOUT", error="request timed out",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        except Exception as e:
            return ProviderResult(
                provider=self.name, indicator=indicator, indicator_type=indicator_type,
                status="ERROR", error=str(e)[:500],
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        res.latency_ms = int((time.perf_counter() - start) * 1000)
        return res