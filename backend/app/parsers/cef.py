from __future__ import annotations

import re
from datetime import datetime

from dateutil import parser as dtparser

from app.parsers.base import BaseParser, DetectionResult, ParseResult

_CEF_HEADER = re.compile(
    r"^(?:[A-Z]{3}\s\d{1,2}\s\d{2}:\d{2}:\d{2}\s\S+\s)?CEF:(?P<ver>\d+)\|"
    r"(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|(?P<devver>[^|]*)\|"
    r"(?P<sig>[^|]*)\|(?P<name>[^|]*)\|(?P<sev>[^|]*)\|(?P<ext>.*)$"
)


def _parse_extensions(ext: str) -> dict:
    """CEF extension: key=value pairs where '=' inside values is escaped as '\\='."""
    result: dict[str, str] = {}
    if not ext:
        return result
    # Split on unescaped spaces
    parts = re.split(r"(?<!\\) ", ext)
    for p in parts:
        if "=" not in p:
            continue
        k, _, v = p.partition("=")
        k = k.strip()
        v = v.replace("\\=", "=").replace("\\|", "|").replace("\\n", "\n").replace("\\\\", "\\")
        if k:
            result[k] = v
    return result


_SEVERITY_MAP = {
    "0": "INFO", "1": "INFO", "2": "INFO", "3": "LOW",
    "4": "LOW", "5": "MEDIUM", "6": "MEDIUM", "7": "HIGH",
    "8": "HIGH", "9": "CRITICAL", "10": "CRITICAL",
    "Unknown": "INFO", "": "INFO",
}


class CEFParser(BaseParser):
    parser_id = "cef"
    name = "ArcSight Common Event Format"
    vendor = "arcsight"
    format_name = "CEF"
    version = "1.0.0"

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        reasons: list[str] = []
        conf = 0.0
        first = raw.strip().splitlines()[0] if raw.strip() else ""
        if "CEF:" in first:
            reasons.append("CEF: prefix detected")
            conf += 0.6
        if re.search(r"CEF:\d+\|", first):
            reasons.append("CEF version and pipe-delimited header detected")
            conf += 0.25
        if "|" in first and "=" in first:
            reasons.append("Pipe-delimited header and key=value extension structure")
            conf += 0.15
        return DetectionResult(format="CEF", confidence=min(conf, 1.0), reasons=reasons)

    def parse(self, raw: str) -> ParseResult:
        line = raw.strip().splitlines()[0] if raw.strip() else ""
        m = _CEF_HEADER.match(line)
        if not m:
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=["CEF header not matched"])
        g = m.groupdict()
        ext = _parse_extensions(g["ext"])

        ts_raw = ext.get("rt") or ext.get("start") or ext.get("end")
        try:
            ts = dtparser.parse(ts_raw) if ts_raw else None
        except Exception:
            ts = None

        fields: dict = {
            "timestamp": ts.isoformat() if ts else None,
            "cef_version": g["ver"],
            "vendor": g["vendor"],
            "product": g["product"],
            "device_version": g["devver"],
            "signature_id": g["sig"],
            "name": g["name"],
            "severity": _SEVERITY_MAP.get(g["sev"], "INFO"),
            "format": "CEF",
            **ext,
        }
        return ParseResult(
            success=True,
            fields=fields,
            raw_message=line,
            parser_id=self.parser_id,
            parser_version=self.version,
            vendor=g["vendor"] or "arcsight",
            product=g["product"] or None,
        )