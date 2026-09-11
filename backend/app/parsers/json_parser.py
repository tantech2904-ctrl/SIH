from __future__ import annotations

import json

from app.parsers.base import BaseParser, DetectionResult, ParseResult


class JSONParser(BaseParser):
    parser_id = "json"
    name = "JSON Object"
    vendor = "generic"
    format_name = "JSON"
    version = "1.0.0"

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        s = raw.strip()
        if not s:
            return DetectionResult("JSON", 0.0, [])
        if s.count("\n") > 0 and s.splitlines()[0].strip().startswith("{"):
            # likely JSONL, not JSON
            return DetectionResult("JSON", 0.15, ["multi-line content starting with {"])
        if not (s.startswith("{") or s.startswith("[")):
            return DetectionResult("JSON", 0.0, [])
        try:
            json.loads(s)
            return DetectionResult("JSON", 0.95, ["Valid JSON document parsed", "Starts with { or ["])
        except json.JSONDecodeError as e:
            return DetectionResult("JSON", 0.3, [f"Starts with {s[:1]} but JSON parse failed: {e.msg}"])

    def parse(self, raw: str) -> ParseResult:
        try:
            obj = json.loads(raw)
        except Exception as e:
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=[f"JSON parse error: {e}"])
        if not isinstance(obj, dict):
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=["Top-level JSON must be an object"])
        fields = dict(obj)
        fields.setdefault("format", "JSON")
        return ParseResult(
            success=True, fields=fields, raw_message=raw,
            parser_id=self.parser_id, parser_version=self.version, vendor="generic",
        )