from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetectionResult:
    format: str
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    success: bool
    fields: dict[str, Any] = field(default_factory=dict)
    raw_message: str = ""
    parser_id: str = ""
    parser_version: str = "1.0.0"
    vendor: str | None = None
    product: str | None = None
    errors: list[str] = field(default_factory=list)
    # candidate canonical mappings discovered for this parse:
    field_confidence: dict[str, float] = field(default_factory=dict)


class BaseParser(ABC):
    """All parsers must be pure functions of their input — no side effects."""

    parser_id: str = "base"
    name: str = "Base Parser"
    vendor: str = "generic"
    format_name: str = "unknown"
    version: str = "1.0.0"

    @abstractmethod
    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        ...

    @abstractmethod
    def parse(self, raw: str) -> ParseResult:
        ...

    def validate(self, parsed: ParseResult) -> list[str]:
        return list(parsed.errors)

    def normalize(self, parsed: ParseResult) -> dict[str, Any]:
        """Default no-op mapping; concrete parsers override via mapper."""
        return parsed.fields

    def metadata(self) -> dict[str, Any]:
        return {
            "parser_id": self.parser_id,
            "name": self.name,
            "vendor": self.vendor,
            "format": self.format_name,
            "version": self.version,
        }