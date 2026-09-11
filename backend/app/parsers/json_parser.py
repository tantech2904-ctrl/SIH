from __future__ import annotations

import json
import re

from app.parsers.base import BaseParser, DetectionResult, ParseResult


class JSONParser(BaseParser):
    parser_id = "json"
    name = "JSON Object"
    vendor = "generic"
    format_name = "JSON"
    version = "1.0.0"

    @staticmethod
    def _strip_comments(raw: str) -> str:
        result: list[str] = []
        in_string = False
        escaped = False
        i = 0
        length = len(raw)

        while i < length:
            ch = raw[i]
            nxt = raw[i + 1] if i + 1 < length else ""

            if in_string:
                result.append(ch)
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue

            if ch == '"':
                in_string = True
                result.append(ch)
                i += 1
                continue

            if ch == "/" and nxt == "/":
                while i < length and raw[i] != "\n":
                    i += 1
                continue

            if ch == "/" and nxt == "*":
                i += 2
                while i < length - 1 and not (raw[i] == "*" and raw[i + 1] == "/"):
                    i += 1
                i += 2
                continue

            if ch == "#":
                while i < length and raw[i] != "\n":
                    i += 1
                continue

            result.append(ch)
            i += 1

        return "".join(result)

    @classmethod
    def _normalize_hjson(cls, raw: str) -> str | None:
        stripped = cls._strip_comments(raw).strip()
        if not stripped or not (stripped.startswith("{") or stripped.startswith("[")):
            return None

        normalized = re.sub(r",(\s*[}\]])", r"\1", stripped)
        normalized = re.sub(
            r"([,{\[]\s*)([A-Za-z_@][A-Za-z0-9_\-@.]*)\s*:",
            lambda m: f"{m.group(1)}\"{m.group(2)}\":",
            normalized,
        )
        return normalized

    @classmethod
    def _parse_json_like(cls, raw: str):
        try:
            return json.loads(raw), None
        except json.JSONDecodeError as exc:
            normalized = cls._normalize_hjson(raw)
            if normalized is None:
                return None, exc
            try:
                return json.loads(normalized), normalized
            except json.JSONDecodeError as exc2:
                return None, exc2

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        s = raw.strip()
        if not s:
            return DetectionResult("JSON", 0.0, [])
        if not (s.startswith("{") or s.startswith("[")):
            return DetectionResult("JSON", 0.0, [])

        obj, normalized = self._parse_json_like(s)
        if obj is not None:
            if normalized is None:
                return DetectionResult("JSON", 0.95, ["Valid JSON document parsed", "Starts with { or ["])
            return DetectionResult(
                "JSON",
                0.85,
                ["HJSON-like content normalized and parsed", "Comments, trailing commas, and unquoted keys were tolerated"],
            )

        return DetectionResult("JSON", 0.25, ["Starts with { or [ but JSON parse failed"])

    def parse(self, raw: str) -> ParseResult:
        obj, _ = self._parse_json_like(raw)
        if obj is None:
            return ParseResult(
                success=False,
                parser_id=self.parser_id,
                parser_version=self.version,
                errors=["JSON parse error: input is not valid JSON or HJSON-like JSON"],
            )
        if not isinstance(obj, dict):
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=["Top-level JSON must be an object"])
        fields = dict(obj)
        fields.setdefault("format", "JSON")
        return ParseResult(
            success=True, fields=fields, raw_message=raw,
            parser_id=self.parser_id, parser_version=self.version, vendor="generic",
        )