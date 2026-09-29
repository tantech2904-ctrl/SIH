"""DNS provider — passive DNS lookups via public resolvers (best-effort).

Runs in a thread pool so we can enforce a timeout without blocking the event loop.
"""
from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from app.core.config import settings
from app.enrichment.base import ProviderResult, ThreatIntelProvider

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ulpf-dns")


def _reverse(ip: str) -> str | None:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None


def _forward(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
        out = sorted({i[4][0] for i in infos})
        return out
    except Exception:
        return []


class DNSProvider(ThreatIntelProvider):
    name = "DNS"
    indicator_types = ("ip", "domain")

    def is_configured(self) -> bool:
        return bool(settings.DNS_ENABLED)

    def lookup(self, indicator: str, indicator_type: str) -> ProviderResult:
        if indicator_type == "ip":
            fut = _executor.submit(_reverse, indicator)
            try:
                ptr = fut.result(timeout=settings.ENRICHMENT_HTTP_TIMEOUT_SECONDS)
            except FutureTimeout:
                fut.cancel()
                return ProviderResult(self.name, indicator, indicator_type, "TIMEOUT", {}, error="reverse DNS timeout")
            return ProviderResult(self.name, indicator, indicator_type, "OK",
                                   {"reverse_dns": ptr})
        if indicator_type == "domain":
            fut = _executor.submit(_forward, indicator)
            try:
                addrs = fut.result(timeout=settings.ENRICHMENT_HTTP_TIMEOUT_SECONDS)
            except FutureTimeout:
                fut.cancel()
                return ProviderResult(self.name, indicator, indicator_type, "TIMEOUT", {}, error="DNS timeout")
            return ProviderResult(self.name, indicator, indicator_type, "OK",
                                   {"forward_dns": addrs})
        return ProviderResult(self.name, indicator, indicator_type, "OK",
                               {"skipped": "unsupported_type"})