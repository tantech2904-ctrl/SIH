from __future__ import annotations

from typing import Iterable

from app.parsers.base import BaseParser
from app.parsers.rfc5424 import RFC5424Parser
from app.parsers.cef import CEFParser
from app.parsers.leef import LEEFParser
from app.parsers.json_parser import JSONParser
from app.parsers.jsonl import JSONLParser
from app.parsers.xml_parser import XMLParser
from app.parsers.csv_parser import CSVParser
from app.parsers.windows_evtx import WindowsEventLogParser


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
        _registry = r
    return _registry