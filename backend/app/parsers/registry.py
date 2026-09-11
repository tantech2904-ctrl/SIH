from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from app.parsers.base import BaseParser, DetectionResult, ParseResult
from app.parsers.rfc5424 import RFC5424Parser
from app.parsers.cef import CEFParser
from app.parsers.leef import LEEFParser
from app.parsers.json_parser import JSONParser
from app.parsers.jsonl import JSONLParser
from app.parsers.xml_parser import XMLParser
from app.parsers.csv_parser import CSVParser
from app.parsers.windows_evtx import WindowsEventLogParser


class DynamicParser(BaseParser):
    """Parser backed by a JSON definition file from the plug-and-play parsers directory."""

    def __init__(self, definition: dict[str, object]) -> None:
        self.definition = definition
        self.parser_id = str(definition.get("name") or definition.get("parser_id") or "dynamic")
        self.name = str(definition.get("name") or self.parser_id)
        self.vendor = str(definition.get("vendor") or "generic")
        self.format_name = str(definition.get("format") or "unknown")
        self.version = str(definition.get("version") or "1.0.0")
        self.description = str(definition.get("description") or "")
        self.match_criteria = definition.get("match_criteria") or {}
        self.extraction = definition.get("extraction") or {}
        self.field_mappings = definition.get("field_mappings") or {}

    def _contains_hits(self, raw: str) -> list[str]:
        criteria = self.match_criteria or {}
        contains = criteria.get("contains") or []
        if not isinstance(contains, list):
            return []
        return [item for item in contains if isinstance(item, str) and item in raw]

    def _regex_hits(self, raw: str) -> list[str]:
        criteria = self.match_criteria or {}
        regex = criteria.get("regex")
        if not regex:
            return []
        try:
            if re.search(regex, raw, re.IGNORECASE | re.MULTILINE):
                return [regex]
        except Exception:
            return []
        return []

    def _kv_pairs(self, raw: str) -> dict[str, str]:
        delimiter = self.extraction.get("delimiter") or " "
        kv_separator = self.extraction.get("kv_separator") or "="
        if delimiter in {",", ";", "|", " ", "\t"}:
            delimiter_candidates = [delimiter]
        else:
            delimiter_candidates = [delimiter, " ", "\t"]

        fields: dict[str, str] = {}
        if self.extraction.get("type") == "key-value":
            pattern = re.compile(r'([A-Za-z0-9_\.\-]+)\s*' + re.escape(kv_separator) + r'\s*(?:"([^"]*)"|([^\s,;|]+))')
            for match in pattern.finditer(raw):
                key = match.group(1)
                value = match.group(2) if match.group(2) is not None else match.group(3)
                fields[key] = value

        if not fields and delimiter_candidates:
            for token in re.split(r'[\t ;|,]+', raw):
                if kv_separator not in token:
                    continue
                key, value = token.split(kv_separator, 1)
                key = key.strip()
                value = value.strip().strip('"')
                if key:
                    fields[key] = value

        return fields

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        text = raw.strip()
        if not text:
            return DetectionResult(self.format_name, 0.0, [])

        reasons: list[str] = []
        confidence = 0.0

        contains_hits = self._contains_hits(text)
        if contains_hits:
            confidence = max(confidence, 0.35)
            reasons.append(f"Match criteria contains {len(contains_hits)} required token(s)")

        regex_hits = self._regex_hits(text)
        if regex_hits:
            confidence = max(confidence, 0.55)
            reasons.append("Match criteria regex matched")

        extraction_type = str(self.extraction.get("type") or "").lower()
        if extraction_type == "regex":
            pattern = self.extraction.get("pattern")
            if isinstance(pattern, str):
                try:
                    if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                        confidence = max(confidence, 0.75)
                        reasons.append("Extraction regex matched")
                except Exception:
                    pass
        elif extraction_type == "key-value":
            kv_pairs = self._kv_pairs(text)
            if kv_pairs:
                confidence = max(confidence, 0.45)
                reasons.append(f"Parsed {len(kv_pairs)} key-value pairs")

        if confidence <= 0.0:
            return DetectionResult(self.format_name, 0.0, reasons or ["No parser-specific signal found"])

        return DetectionResult(self.format_name, min(confidence, 1.0), reasons)

    def parse(self, raw: str) -> ParseResult:
        text = raw.strip()
        extraction_type = str(self.extraction.get("type") or "").lower()

        if extraction_type == "regex":
            pattern = self.extraction.get("pattern")
            if not isinstance(pattern, str):
                return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version,
                                   errors=["Regex parser is missing an extraction pattern"])
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            except Exception as exc:
                return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version,
                                   errors=[f"Regex parse failed: {exc}"])
            if not match:
                return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version,
                                   errors=["Regex extraction did not match the input"])
            fields = match.groupdict() or {}
            if not fields:
                fields = {f"group_{i}": match.group(i) for i in range(1, len(match.groups()) + 1)}
            fields["format"] = self.format_name
            return ParseResult(success=True, fields=fields, raw_message=raw,
                               parser_id=self.parser_id, parser_version=self.version,
                               vendor=self.vendor, product=str(self.definition.get("product") or None))

        if extraction_type == "key-value":
            fields = self._kv_pairs(text)
            if not fields:
                return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version,
                                   errors=["Key-value extraction did not yield any fields"])
            fields["format"] = self.format_name
            return ParseResult(success=True, fields=fields, raw_message=raw,
                               parser_id=self.parser_id, parser_version=self.version,
                               vendor=self.vendor, product=str(self.definition.get("product") or None))

        return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version,
                           errors=[f"Unsupported extraction type: {extraction_type}"])

    def metadata(self) -> dict[str, object]:
        return {
            "parser_id": self.parser_id,
            "name": self.name,
            "vendor": self.vendor,
            "format": self.format_name,
            "version": self.version,
            "extra": {
                "description": self.description,
                "match_criteria": self.match_criteria,
                "extraction": self.extraction,
                "field_mappings": self.field_mappings,
            },
        }


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}
        self._order: list[str] = []

    def register(self, parser: BaseParser) -> None:
        self._parsers[parser.parser_id] = parser
        if parser.parser_id not in self._order:
            self._order.append(parser.parser_id)

    def get(self, parser_id: str) -> BaseParser | None:
        return self._parsers.get(parser_id)

    def all(self) -> Iterable[BaseParser]:
        return [self._parsers[pid] for pid in self._order]

    def list_metadata(self) -> dict[str, dict]:
        return {pid: self._parsers[pid].metadata() for pid in self._order}

    def best_match(self, raw: str, *, filename: str | None = None) -> tuple[BaseParser | None, object]:
        best: BaseParser | None = None
        best_result = None
        for p in self.all():
            try:
                res = p.detect(raw, filename=filename)
            except Exception:
                continue
            if best_result is None or res.confidence > best_result.confidence:
                best, best_result = p, res
        return best, best_result

    def load_parsers_from_directory(self, base_dir: str | Path) -> int:
        base_path = Path(base_dir)
        if not base_path.exists():
            return 0

        loaded = 0
        for file_path in sorted(base_path.rglob("*.json")):
            if file_path.name == "schema" or file_path.name.endswith(".schema.json"):
                continue
            try:
                config = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(config, dict):
                continue
            name = config.get("name") or config.get("parser_id")
            if not name:
                continue
            parser = DynamicParser(config)
            self.register(parser)
            loaded += 1
        return loaded


_registry: ParserRegistry | None = None


def get_registry() -> ParserRegistry:
    global _registry
    if _registry is None:
        r = ParserRegistry()
        r.register(RFC5424Parser())
        r.register(CEFParser())
        r.register(LEEFParser())
        r.register(JSONParser())
        r.register(JSONLParser())
        r.register(XMLParser())
        r.register(CSVParser())
        r.register(WindowsEventLogParser())

        repo_root = Path(__file__).resolve().parents[3]
        plugin_dirs = [
            repo_root / "parsers",
            repo_root.parent / "SIH-2026-LOG-FRAMEWORK" / "parsers",
        ]
        for plugin_dir in plugin_dirs:
            if plugin_dir.exists():
                r.load_parsers_from_directory(plugin_dir)

        _registry = r
    return _registry