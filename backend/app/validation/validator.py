"""CSE validation.

Validates the normalized event against a canonical schema:
- Required fields present
- Types correct (IP, port, timestamp, severity)
- Consistency rules

Returns VALID | WARNING | INVALID plus a list of notes.
Never silently drops invalid events — the pipeline quarantines them.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from datetime import datetime

from dateutil import parser as dtparser

from app.normalization.vocabulary import SEVERITY_ORDER


@dataclass
class ValidationResult:
    status: str = "VALID"  # VALID|WARNING|INVALID
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"status": self.status, "notes": self.notes}


REQUIRED = ["timestamp", "event_type", "category", "severity"]


def validate_cse(cse: dict) -> ValidationResult:
    notes: list[str] = []
    invalid = False

    for req in REQUIRED:
        if cse.get(req) in (None, ""):
            notes.append(f"Missing required field: {req}")
            invalid = True

    # Timestamp
    ts = cse.get("timestamp")
    if ts:
        try:
            dt = dtparser.parse(str(ts))
            # Naive timestamps → warn
            if dt.tzinfo is None:
                notes.append("Timestamp has no timezone; assuming UTC")
        except Exception:
            notes.append("Timestamp is not parseable")
            invalid = True

    # Severity
    sev = (cse.get("severity") or "").upper()
    if sev and sev not in SEVERITY_ORDER:
        notes.append(f"Unknown severity value: {sev}")
        invalid = True

    # IPs
    for ipf in ("source.ip", "destination.ip", "extensions.ip"):
        ip = cse.get(ipf)
        if ip:
            try:
                ipaddress.ip_address(str(ip))
            except ValueError:
                notes.append(f"Invalid IP in {ipf}: {ip}")
                invalid = True

    # Ports
    for pf in ("source.port", "destination.port"):
        p = cse.get(pf)
        if p is not None:
            try:
                n = int(p)
                if not (0 <= n <= 65535):
                    raise ValueError
            except Exception:
                notes.append(f"Invalid port in {pf}: {p}")
                invalid = True

    # Event-type sanity
    et = (cse.get("event_type") or "").lower()
    if et == "unknown":
        notes.append("event_type is 'unknown' — low confidence normalization")

    if invalid:
        return ValidationResult(status="INVALID", notes=notes)
    if notes:
        return ValidationResult(status="WARNING", notes=notes)
    return ValidationResult(status="VALID", notes=[])