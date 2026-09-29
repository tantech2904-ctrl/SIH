from __future__ import annotations

import re
from datetime import datetime

from dateutil import parser as dtparser

from app.parsers.base import BaseParser, DetectionResult, ParseResult

# RFC5424: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG
_RFC5424 = re.compile(
    r"^<(?P<pri>\d{1,3})>(?P<ver>\d)\s"
    r"(?P<ts>\S+)\s(?P<host>\S+)\s(?P<app>\S+)\s(?P<procid>\S+)\s(?P<msgid>\S+)\s"
    r"(?P<sd>-|\[.*?\])\s?(?P<msg>.*)$"
)

_SEVERITY_MAP = {0: "CRITICAL", 1: "CRITICAL", 2: "CRITICAL", 3: "HIGH", 4: "MEDIUM", 5: "LOW", 6: "INFO", 7: "INFO"}


class RFC5424Parser(BaseParser):
    parser_id = "rfc5424"
    name = "RFC 5424 Syslog"
    vendor = "ietf"
    format_name = "RFC5424"
    version = "1.0.0"

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        reasons: list[str] = []
        conf = 0.0
        first_line = raw.strip().splitlines()[0] if raw.strip() else ""
        if first_line.startswith("<") and ">" in first_line[:5]:
            reasons.append("Priority prefix <PRI> detected")
            conf += 0.4
        if re.match(r"^<\d{1,3}>\d\s", first_line):
            reasons.append("Version digit after PRI (RFC 5424 signature)")
            conf += 0.5
        if re.match(r"^<\d{1,3}>\d\s\S+\s\S+\s\S+\s\S+\s\S+\s", first_line):
            reasons.append("Full RFC 5424 header structure present")
            conf += 0.1
        return DetectionResult(format="RFC5424", confidence=min(conf, 1.0), reasons=reasons)

    def parse(self, raw: str) -> ParseResult:
        line = raw.strip().splitlines()[0] if raw.strip() else ""
        m = _RFC5424.match(line)
        if not m:
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=["RFC5424 header not matched"])
        g = m.groupdict()
        try:
            ts = dtparser.parse(g["ts"]) if g["ts"] != "-" else None
        except Exception:
            ts = None
        pri = int(g["pri"])
        sev_num = pri % 8
        facility = pri // 8
        fields = {
            "timestamp": ts.isoformat() if ts else None,
            "priority": pri,
            "facility": facility,
            "severity_num": sev_num,
            "severity": _SEVERITY_MAP.get(sev_num, "INFO"),
            "hostname": g["host"],
            "app_name": g["app"],
            "procid": g["procid"],
            "msgid": g["msgid"],
            "structured_data": g["sd"],
            "message": g["msg"],
            "format": "RFC5424",
        }
        return ParseResult(
            success=True,
            fields=fields,
            raw_message=line,
            parser_id=self.parser_id,
            parser_version=self.version,
            vendor="ietf",
        )