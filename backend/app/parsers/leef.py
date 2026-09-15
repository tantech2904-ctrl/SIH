from __future__ import annotations

import re

from dateutil import parser as dtparser

from app.parsers.base import BaseParser, DetectionResult, ParseResult

# LEEF:1.0|Vendor|Product|Version|EventID|attribute1=value1<TAB>attribute2=value2
_LEEF_HEADER = re.compile(
    r"^LEEF:(?P<ver>[\d.]+)\|(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|(?P<devver>[^|]*)\|"
    r"(?P<eventid>[^|]*)\|?(?P<attrs>.*)$"
)


def _parse_attrs(attrs: str, delimiter: str) -> dict:
    result: dict[str, str] = {}
    if not attrs:
        return result
    # Delimiter may be a literal tab or custom
    parts = attrs.split(delimiter)
    for p in parts:
        if not p or "=" not in p:
            continue
        k, _, v = p.partition("=")
        k = k.strip()
        if k:
            result[k] = v
    return result


class LEEFParser(BaseParser):
    parser_id = "leef"
    name = "IBM QRadar LEEF"
    vendor = "ibm"
    format_name = "LEEF"
    version = "1.0.0"

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        reasons: list[str] = []
        conf = 0.0
        first = raw.strip().splitlines()[0] if raw.strip() else ""
        if first.startswith("LEEF:"):
            reasons.append("LEEF: prefix detected")
            conf += 0.6
        if re.match(r"^LEEF:[\d.]+\|", first):
            reasons.append("LEEF version and pipe-delimited header")
            conf += 0.25
        if "\t" in first or re.search(r"[A-Za-z_]+=[^|\t]+", first):
            reasons.append("Attribute key=value pairs present")
            conf += 0.15
        return DetectionResult(format="LEEF", confidence=min(conf, 1.0), reasons=reasons)

    def parse(self, raw: str) -> ParseResult:
        line = raw.strip().splitlines()[0] if raw.strip() else ""
        m = _LEEF_HEADER.match(line)
        if not m:
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=["LEEF header not matched"])
        g = m.groupdict()
        delimiter = "\t" if "\t" in g["attrs"] else "^"
        attrs = _parse_attrs(g["attrs"], delimiter)

        ts_raw = attrs.get("devTime") or attrs.get("devTimeFormat")
        try:
            ts = dtparser.parse(ts_raw) if ts_raw else None
        except Exception:
            ts = None

        fields = {
            "timestamp": ts.isoformat() if ts else None,
            "leef_version": g["ver"],
            "vendor": g["vendor"],
            "product": g["product"],
            "device_version": g["devver"],
            "event_id": g["eventid"],
            "format": "LEEF",
            **attrs,
        }
        return ParseResult(
            success=True,
            fields=fields,
            raw_message=line,
            parser_id=self.parser_id,
            parser_version=self.version,
            vendor=g["vendor"] or "ibm",
            product=g["product"] or None,
        )