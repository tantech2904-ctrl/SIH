"""Canonical Security Event (CSE) construction.

The mapper takes a parser's field dictionary, resolves each original field to
a canonical path, applies the transformation, and produces:
  - CSE field values ready to persist on CanonicalEvent
  - a provenance list recording (original → canonical, transformation, source)
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as dtparser

from app.normalization.vocabulary import (
    CSE_FIELDS,
    SEVERITY_ORDER,
    lookup_alias,
    severity_rank,
)


@dataclass
class MappingRecord:
    original_field: str
    original_value: str
    canonical_field: str
    transformation: str
    confidence: float
    source: str  # builtin|analyst|analyzer
    parser_id: str = ""
    parser_version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "original_field": self.original_field,
            "original_value": self.original_value,
            "canonical_field": self.canonical_field,
            "transformation": self.transformation,
            "confidence": self.confidence,
            "source": self.source,
            "parser_id": self.parser_id,
            "parser_version": self.parser_version,
        }


@dataclass
class CSEResult:
    fields: dict[str, Any] = field(default_factory=dict)          # canonical-path → value
    provenance: list[MappingRecord] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)

    def __getitem__(self, key: str):
        if key == "fields":
            return self.fields
        if key == "provenance":
            return self.provenance
        if key == "unmapped":
            return self.unmapped
        raise KeyError(key)


def _to_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        import json
        try:
            return json.dumps(v, separators=(",", ":"))[:2048]
        except Exception:
            return str(v)[:2048]
    return str(v)


def _parse_ts(v: Any) -> str | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        try:
            # Heuristic: > 10^12 → ms, else s
            ts = float(v)
            if ts > 1e12:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except Exception:
            return None
    try:
        dt = dtparser.parse(str(v))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def _parse_port(v: Any) -> int | None:
    try:
        n = int(str(v).strip())
        if 0 <= n <= 65535:
            return n
    except Exception:
        return None
    return None


def _parse_ip(v: Any) -> str | None:
    try:
        ip = ipaddress.ip_address(str(v).strip())
        return str(ip)
    except Exception:
        return None


def _parse_severity(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in SEVERITY_ORDER:
        return s
    # Numeric CEF/LEEF-like severity
    if s.isdigit():
        n = int(s)
        if n <= 2:
            return "INFO"
        if n <= 4:
            return "LOW"
        if n <= 6:
            return "MEDIUM"
        if n <= 8:
            return "HIGH"
        return "CRITICAL"
    # Syslog word severities
    mapping = {
        "EMERG": "CRITICAL", "ALERT": "CRITICAL", "CRIT": "CRITICAL", "CRITICAL": "CRITICAL",
        "ERR": "HIGH", "ERROR": "HIGH", "HIGH": "HIGH",
        "WARNING": "MEDIUM", "WARN": "MEDIUM", "MEDIUM": "MEDIUM",
        "NOTICE": "LOW", "LOW": "LOW",
        "DEBUG": "INFO", "INFO": "INFO", "INFORMATIONAL": "INFO",
    }
    return mapping.get(s)


_TRANSFORMS = {
    "timestamp": ("timestamp_parse", _parse_ts),
    "source.port": ("port_parse", _parse_port),
    "destination.port": ("port_parse", _parse_port),
    "source.ip": ("ip_parse", _parse_ip),
    "destination.ip": ("ip_parse", _parse_ip),
    "extensions.ip": ("ip_parse", _parse_ip),
    "severity": ("severity_normalize", _parse_severity),
}


def _apply_transform(canonical: str, value: Any) -> tuple[str, Any]:
    if canonical in _TRANSFORMS:
        name, fn = _TRANSFORMS[canonical]
        return name, fn(value)
    return "direct", value


def _infer_event_type(fields: dict[str, Any]) -> str:
    """Best-effort event_type inference using presence of canonical fields."""
    explicit = fields.get("event_type")
    if explicit:
        return str(explicit).lower()
    # Heuristics
    msg = (str(fields.get("name", "")) + " " + str(fields.get("message", ""))).lower()
    if any(k in msg for k in ["login", "logon", "auth", "signin", "sign-in", "logout"]):
        return "authentication"
    if any(k in msg for k in ["denied", "blocked", "firewall", "drop"]):
        return "network"
    if any(k in msg for k in ["malware", "virus", "trojan", "hash"]):
        return "malware"
    if any(k in msg for k in ["scan", "port_scan"]):
        return "network"
    if any(k in msg for k in ["cve-", "vulnerability", "exploit"]):
        return "vulnerability"
    if any(k in msg for k in ["sudo", "privilege", "escalat", "admin"]):
        return "privilege_escalation"
    if "dns" in msg:
        return "dns"
    if fields.get("source.ip") or fields.get("destination.ip"):
        return "network"
    return "unknown"


def _infer_category(fields: dict[str, Any], event_type: str) -> str:
    explicit = fields.get("category")
    if explicit:
        return str(explicit).lower()
    mapping = {
        "authentication": "iam",
        "privilege_escalation": "iam",
        "network": "network_activity",
        "malware": "security_finding",
        "vulnerability": "security_finding",
        "dns": "network_activity",
    }
    return mapping.get(event_type, "other")


class CSEMapper:
    """Maps a parser's field dict into CSE canonical fields + provenance."""

    def __init__(self, *, parser_id: str = "", parser_version: str = "1.0.0",
                 custom_mappings: dict[str, dict] | None = None):
        self.parser_id = parser_id
        self.parser_version = parser_version
        # custom_mappings: {original_field: {"canonical": str, "confidence": float, "source": str}}
        self.custom_mappings = custom_mappings or {}

    def map(self, parsed_fields: dict[str, Any]) -> CSEResult:
        result = CSEResult()
        # seed with format marker
        if "format" in parsed_fields:
            result.fields["format"] = parsed_fields["format"]

        for original_field, raw_value in parsed_fields.items():
            if original_field in {"format"}:
                continue
            value_str = _to_str(raw_value)
            canonical, conf, source = self._resolve(original_field, raw_value)
            if not canonical:
                result.unmapped.append(original_field)
                continue
            transform_name, transformed = _apply_transform(canonical, raw_value)
            if transformed is None and canonical in {"source.ip", "destination.ip", "extensions.ip",
                                                      "source.port", "destination.port",
                                                      "timestamp", "severity"}:
                # transform failed for a typed field → record as unmapped candidate
                result.unmapped.append(original_field)
                continue
            # Special-case: extensions.* nests into extensions dict
            if canonical.startswith("extensions."):
                ext_key = canonical.split(".", 1)[1]
                result.fields.setdefault("extensions", {})[ext_key] = transformed
            else:
                result.fields[canonical] = transformed
            result.provenance.append(MappingRecord(
                original_field=original_field,
                original_value=value_str[:512],
                canonical_field=canonical,
                transformation=transform_name,
                confidence=conf,
                source=source,
                parser_id=self.parser_id,
                parser_version=self.parser_version,
            ))

        # Derived fields
        if "event_type" not in result.fields:
            inferred = _infer_event_type(result.fields)
            result.fields["event_type"] = inferred
            result.provenance.append(MappingRecord(
                original_field="<inferred>", original_value="", canonical_field="event_type",
                transformation="heuristic_inference", confidence=0.5, source="builtin",
                parser_id=self.parser_id, parser_version=self.parser_version,
            ))
        if "category" not in result.fields:
            result.fields["category"] = _infer_category(result.fields, result.fields["event_type"])
            result.provenance.append(MappingRecord(
                original_field="<derived>", original_value="", canonical_field="category",
                transformation="derived_from_event_type", confidence=0.5, source="builtin",
                parser_id=self.parser_id, parser_version=self.parser_version,
            ))
        if "severity" not in result.fields:
            result.fields["severity"] = "INFO"
            result.provenance.append(MappingRecord(
                original_field="<default>", original_value="", canonical_field="severity",
                transformation="default", confidence=1.0, source="builtin",
                parser_id=self.parser_id, parser_version=self.parser_version,
            ))
        if "timestamp" not in result.fields:
            result.fields["timestamp"] = datetime.now(timezone.utc).isoformat()
            result.provenance.append(MappingRecord(
                original_field="<fallback>", original_value="", canonical_field="timestamp",
                transformation="server_time_fallback", confidence=0.3, source="builtin",
                parser_id=self.parser_id, parser_version=self.parser_version,
            ))
        return result

    def _resolve(self, field: str, value: Any) -> tuple[str | None, float, str]:
        # 1. analyst-approved custom mapping
        if field in self.custom_mappings:
            m = self.custom_mappings[field]
            return m["canonical"], float(m.get("confidence", 1.0)), m.get("source", "analyst")

        # 2. Semantic alias table
        canon = lookup_alias(field)
        if canon:
            return canon, 0.95, "builtin"

        # 3. Parser-specific mapping table (fall through to alias table already covered)
        #    Additional parser mappings can be added to SEMANTIC_ALIASES without code changes.
        return None, 0.0, ""