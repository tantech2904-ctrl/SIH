from __future__ import annotations

import json

from app.parsers.base import BaseParser, DetectionResult, ParseResult


class JSONLParser(BaseParser):
    parser_id = "jsonl"
    name = "JSON Lines"
    vendor = "generic"
    format_name = "JSONL"
    version = "1.0.0"

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if len(lines) < 2:
            return DetectionResult("JSONL", 0.0, [])
        valid = 0
        for ln in lines[:8]:
            try:
                json.loads(ln)
                valid += 1
            except Exception:
                pass
        if valid >= 2 and valid == min(len(lines), 8):
            return DetectionResult("JSONL", 0.9, ["Multiple lines each parse as JSON"])
        if valid >= 2:
            return DetectionResult("JSONL", 0.6, [f"{valid}/{min(len(lines),8)} lines parsed as JSON"])
        return DetectionResult("JSONL", 0.0, [])

    def parse(self, raw: str) -> ParseResult:
        # Per-event parsing only takes the first line — batch ingestion splits upstream.
        first = raw.strip().splitlines()[0] if raw.strip() else ""
        try:
            obj = json.loads(first)
        except Exception as e:
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=[f"JSONL line parse error: {e}"])
        if not isinstance(obj, dict):
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=["JSONL line must be an object"])
        fields = dict(obj)
        fields.setdefault("format", "JSONL")
        return ParseResult(success=True, fields=fields, raw_message=first, parser_id=self.parser_id, parser_version=self.version)