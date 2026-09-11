"""Structural analyzer for previously-unseen log formats.

This is one of ULPF's novelty features: when a log cannot be matched to a
known parser, we do not drop it — we structurally analyse it, infer field
types, and suggest canonical mappings for analyst approval.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any

from dateutil import parser as dtparser


_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6 = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,}[0-9a-fA-F]{1,4}\b")
_HOSTNAME = re.compile(r"\b[a-zA-Z][\w-]{1,62}(?:\.[a-zA-Z]{2,})+\b")
_URL = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_HASH_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")
_HASH_SHA1 = re.compile(r"\b[a-fA-F0-9]{40}\b")
_HASH_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PORT = re.compile(r"(?<![\d.])(\d{1,5})(?![\d.])")
_CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)


@dataclass
class FieldCandidate:
    name: str
    value: str
    inferred_types: list[str] = field(default_factory=list)
    suggested_canonical: str | None = None
    confidence: float = 0.0
    reason: str = ""


@dataclass
class AnalysisResult:
    delimiter: str | None
    field_count: int
    candidates: list[FieldCandidate] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _classify_value(v: str) -> list[str]:
    types: list[str] = []
    v_stripped = v.strip()
    if not v_stripped:
        return ["empty"]
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", v_stripped):
        try:
            ipaddress.ip_address(v_stripped)
            types.append("ipv4")
        except ValueError:
            pass
    if _IPV6.fullmatch(v_stripped):
        types.append("ipv6")
    if _URL.fullmatch(v_stripped) or _URL.match(v_stripped):
        types.append("url")
    if _HASH_SHA256.fullmatch(v_stripped):
        types.append("sha256")
    elif _HASH_SHA1.fullmatch(v_stripped):
        types.append("sha1")
    elif _HASH_MD5.fullmatch(v_stripped):
        types.append("md5")
    if _EMAIL.fullmatch(v_stripped):
        types.append("email")
    if _HOSTNAME.fullmatch(v_stripped) and "ipv4" not in types:
        types.append("hostname")
    # timestamp?
    if any(c in v_stripped for c in "-:/T") and len(v_stripped) >= 8:
        try:
            dtparser.parse(v_stripped)
            types.append("timestamp")
        except Exception:
            pass
    # port?
    if v_stripped.isdigit():
        n = int(v_stripped)
        if 0 <= n <= 65535:
            types.append("port_or_int")
    if v_stripped.lower() in {"true", "false"}:
        types.append("bool")
    if " " in v_stripped:
        types.append("text")
    if not types:
        types.append("string")
    return types


def _canonical_from_name(name: str, types: list[str]) -> tuple[str | None, float, str]:
    n = name.lower().replace("-", "_")
    if n in {"src_ip", "source_ip", "srcip", "srcaddress", "client_ip", "clientip", "sourceaddress", "source_addr", "src_addr"}:
        return "source.ip", 0.97, "Name matches source-IP alias set"
    if n in {"dst_ip", "destination_ip", "dstip", "dstaddress", "target_ip", "targetip", "dest_ip", "dest_addr", "dst_addr", "destinationaddress"}:
        return "destination.ip", 0.97, "Name matches destination-IP alias set"
    if n in {"src_port", "source_port", "srcport", "sport", "client_port", "sourceport"}:
        return "source.port", 0.95, "Name matches source-port alias set"
    if n in {"dst_port", "destination_port", "dstport", "dport", "target_port", "destinationport"}:
        return "destination.port", 0.95, "Name matches destination-port alias set"
    if n in {"user", "username", "user_name", "account", "account_name", "principal", "actor", "src_user"}:
        return "user.name", 0.95, "Name matches user alias set"
    if n in {"action", "event_action", "act", "operation", "verb"}:
        return "action", 0.95, "Name matches action alias set"
    if n in {"status", "result", "outcome", "disposition"}:
        return "status", 0.9, "Name matches status alias set"
    if n in {"severity", "sev", "level", "priority", "crit"}:
        return "severity", 0.9, "Name matches severity alias set"
    if n in {"protocol", "proto", "transport"}:
        return "protocol", 0.9, "Name matches protocol alias set"
    if n in {"host", "hostname", "host_name", "computer", "device", "device_name"}:
        return "device", 0.85, "Name matches device/host alias set"
    if n in {"message", "msg", "description", "text"}:
        return "message", 0.9, "Name matches message alias set"
    if n in {"vendor", "manufacturer", "source_vendor"}:
        return "vendor", 0.9, "Name matches vendor alias set"
    if n in {"product", "app", "application"}:
        return "product", 0.85, "Name matches product alias set"
    if n in {"ts", "timestamp", "time", "@timestamp", "event_time", "datetime", "occurred_at"}:
        return "timestamp", 0.95, "Name matches timestamp alias set"
    if n in {"cve", "vulnerability", "vuln_id"}:
        return "extensions.cve", 0.85, "Name matches CVE alias set"
    if n in {"md5", "sha1", "sha256", "hash", "file_hash"}:
        return "extensions.file_hash", 0.9, "Name matches hash alias set"
    if n in {"url", "uri", "request_url", "target_url"}:
        return "extensions.url", 0.9, "Name matches URL alias set"
    if n in {"domain", "fqdn", "dns_name"}:
        return "extensions.domain", 0.9, "Name matches domain alias set"
    # Fallback by value type
    if "ipv4" in types or "ipv6" in types:
        return "extensions.ip", 0.4, "Value looks like an IP but field name is unknown"
    if "timestamp" in types:
        return "timestamp", 0.6, "Value parses as timestamp but field name is ambiguous"
    if "sha256" in types or "sha1" in types or "md5" in types:
        return "extensions.file_hash", 0.7, "Value matches hash pattern"
    if "url" in types:
        return "extensions.url", 0.7, "Value matches URL pattern"
    if "email" in types:
        return "user.email", 0.7, "Value matches email pattern"
    if "port_or_int" in types:
        return None, 0.2, "Integer value; cannot determine role without context"
    return None, 0.0, "No canonical mapping inferred"


def analyze_unknown(raw: str) -> AnalysisResult:
    text = raw.strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    first = lines[0] if lines else text
    notes: list[str] = []

    # Try to detect delimiter
    delimiter = None
    for d in ["|", "\t", ",", ";", " "]:
        parts = first.split(d)
        if len(parts) >= 3 and len(parts) <= 64:
            delimiter = d
            break

    parts = first.split(delimiter) if delimiter else [first]
    candidates: list[FieldCandidate] = []

    # If it looks like key=value pairs
    kv_pairs: dict[str, str] = {}
    for p in re.split(r"\s+", first):
        if "=" in p:
            k, _, v = p.partition("=")
            if k and v:
                kv_pairs[k.strip()] = v.strip()

    if len(kv_pairs) >= 2:
        notes.append(f"Detected {len(kv_pairs)} key=value pairs")
        for k, v in kv_pairs.items():
            types = _classify_value(v)
            canon, conf, reason = _canonical_from_name(k, types)
            candidates.append(FieldCandidate(name=k, value=v, inferred_types=types,
                                              suggested_canonical=canon, confidence=conf, reason=reason))
    else:
        for idx, p in enumerate(parts):
            p = p.strip()
            if not p:
                continue
            types = _classify_value(p)
            name = f"field_{idx}"
            canon, conf, reason = _canonical_from_name(name, types)
            # For positional unknown fields, boost confidence if value is a strong type
            if canon is None and ("ipv4" in types or "ipv6" in types):
                # Assign based on order: first IP → source.ip, second → destination.ip
                prior_ips = sum(1 for c in candidates if c.suggested_canonical in {"source.ip", "destination.ip"})
                if prior_ips == 0:
                    canon, conf, reason = "source.ip", 0.7, "First positional IP address → likely source"
                elif prior_ips == 1:
                    canon, conf, reason = "destination.ip", 0.7, "Second positional IP address → likely destination"
                else:
                    canon, conf, reason = "extensions.ip", 0.5, "Additional IP address"
            candidates.append(FieldCandidate(name=name, value=p, inferred_types=types,
                                              suggested_canonical=canon, confidence=conf, reason=reason))

    return AnalysisResult(
        delimiter=delimiter,
        field_count=len(candidates),
        candidates=candidates,
        notes=notes,
    )