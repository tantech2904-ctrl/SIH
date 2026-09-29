from __future__ import annotations

import re

import xmltodict
from defusedxml import ElementTree as DefusedET  # noqa: F401  (used indirectly)

from app.parsers.base import BaseParser, DetectionResult, ParseResult


class XMLParser(BaseParser):
    parser_id = "xml"
    name = "XML Document"
    vendor = "generic"
    format_name = "XML"
    version = "1.0.0"

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        s = raw.strip()
        if not s:
            return DetectionResult("XML", 0.0, [])
        conf = 0.0
        reasons: list[str] = []
        if s.startswith("<?xml"):
            reasons.append("XML declaration present")
            conf += 0.6
        if re.match(r"^<[A-Za-z_?][\w:.-]*[\s>?]", s):
            reasons.append("Root element opening tag detected")
            conf += 0.3
        if s.startswith("<"):
            conf += 0.05
        # Reject obvious HTML
        if s.lower().startswith("<!doctype html"):
            return DetectionResult("XML", 0.05, ["Looks like HTML"])
        return DetectionResult("XML", min(conf, 1.0), reasons)

    def parse(self, raw: str) -> ParseResult:
        try:
            obj = xmltodict.parse(raw)
        except Exception as e:
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=[f"XML parse error: {e}"])
        if not isinstance(obj, dict) or not obj:
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=["Empty XML object"])
        root_name = next(iter(obj.keys()))
        fields = {"format": "XML", "root": root_name, "xml": obj}
        # Flatten single-level maps for convenience
        root_val = obj[root_name]
        if isinstance(root_val, dict):
            for k, v in root_val.items():
                fields.setdefault(k, v)
        return ParseResult(success=True, fields=fields, raw_message=raw, parser_id=self.parser_id, parser_version=self.version)