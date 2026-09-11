"""Format detector.

Combines parser-declared detections into a single best-match result.
Detection is signal-based (not extension-based). We never claim ML detection.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.parsers.registry import get_registry


@dataclass
class FormatDetection:
    format: str
    parser_id: str
    confidence: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "format": self.format,
            "parser_id": self.parser_id,
            "confidence": round(self.confidence, 4),
            "reasons": self.reasons,
        }


def detect_format(
    raw: str,
    *,
    filename: str | None = None,
    enabled_parser_ids: set[str] | None = None,
) -> FormatDetection:
    registry = get_registry()
    best_parser = None
    best_conf = 0.0
    best_reasons: list[str] = []
    best_format = "UNKNOWN"

    for parser in registry.all():
        if enabled_parser_ids is not None and parser.parser_id not in enabled_parser_ids:
            continue
        try:
            res = parser.detect(raw, filename=filename)
        except Exception:
            continue
        if res.confidence > best_conf:
            best_parser = parser
            best_conf = res.confidence
            best_reasons = res.reasons
            best_format = res.format

    if best_parser is None or best_conf < 0.30:
        return FormatDetection(
            format="UNKNOWN",
            parser_id="",
            confidence=best_conf,
            reasons=best_reasons or ["No parser confidently matched the input"],
        )
    return FormatDetection(
        format=best_format,
        parser_id=best_parser.parser_id,
        confidence=best_conf,
        reasons=best_reasons,
    )