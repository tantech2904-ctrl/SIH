"""SSRF protection utilities.

All outbound HTTP requests triggered by user/event content MUST go through
`validate_outbound_url` and (when calling known providers) the allowlist.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.errors import ULPFError


ALLOWED_PROVIDER_HOSTS = {
    "www.virustotal.com",
    "virustotal.com",
    "otx.alienvault.com",
    "api.abuseipdb.com",
    "rdap.org",
    "rdap.arin.net",
    "rdap.ripe.net",
    "rdap.apnic.net",
    "rdap.lacnic.net",
    "rdap.afrinic.net",
}

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("ff00::/8"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "169.254.169.254",
    "instance-data",
}


class SSRFBlockedError(ULPFError):
    code = "SSRF_BLOCKED"
    http_status = 400


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return any(ip in net for net in BLOCKED_NETWORKS)


def validate_outbound_url(url: str, *, require_allowlist: bool = False) -> str:
    """Validate an outbound URL against SSRF policy. Returns the URL if safe."""
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise SSRFBlockedError("Invalid URL") from e

    if parsed.scheme not in {"http", "https"}:
        raise SSRFBlockedError(f"Scheme not allowed: {parsed.scheme}")

    host = parsed.hostname
    if not host:
        raise SSRFBlockedError("Missing host")

    host_l = host.lower()
    if host_l in BLOCKED_HOSTNAMES:
        raise SSRFBlockedError("Blocked hostname")

    if require_allowlist and host_l not in ALLOWED_PROVIDER_HOSTS:
        raise SSRFBlockedError("Host not in provider allowlist")

    # Resolve & check
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise SSRFBlockedError(f"DNS resolution failed: {e}") from e

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise SSRFBlockedError(f"Resolved IP blocked: {ip_str}")

    return url


def classify_ip(ip_str: str) -> str:
    """Return PRIVATE|LOOPBACK|LINK_LOCAL|MULTICAST|PUBLIC|INVALID."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return "INVALID"
    if ip.is_loopback:
        return "LOOPBACK"
    if ip.is_link_local:
        return "LINK_LOCAL"
    if ip.is_multicast:
        return "MULTICAST"
    if ip.is_private:
        return "PRIVATE"
    return "PUBLIC"