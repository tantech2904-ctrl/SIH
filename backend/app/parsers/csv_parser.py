from __future__ import annotations

import csv
import io

from app.parsers.base import BaseParser, DetectionResult, ParseResult


class CSVParser(BaseParser):
    parser_id = "csv"
    name = "CSV Log"
    vendor = "generic"
    format_name = "CSV"
    version = "1.0.0"

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if len(lines) < 2:
            return DetectionResult("CSV", 0.0, [])
        sample = "\n".join(lines[:5])
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except Exception:
            return DetectionResult("CSV", 0.0, ["CSV dialect not detected"])
        counts = []
        reader = csv.reader(io.StringIO(sample), dialect)
        for row in reader:
            counts.append(len(row))
        if len(counts) >= 2 and len(set(counts[:5])) == 1 and counts[0] > 1:
            return DetectionResult("CSV", 0.85, [f"Consistent delimiter '{dialect.delimiter}' with {counts[0]} columns"])
        return DetectionResult("CSV", 0.3, [f"Delimiter detected '{dialect.delimiter}' but columns vary"])

    def parse(self, raw: str) -> ParseResult:
        sample = raw.strip()
        try:
            dialect = csv.Sniffer().sniff("\n".join(sample.splitlines()[:5]), delimiters=",;\t|")
        except Exception:
            dialect = csv.excel
        reader = csv.reader(io.StringIO(sample), dialect)
        rows = list(reader)
        if len(rows) < 2:
            return ParseResult(success=False, parser_id=self.parser_id, parser_version=self.version, errors=["CSV requires header + at least one row"])
        header = [h.strip() for h in rows[0]]
        data_row = dict(zip(header, rows[1]))
        data_row["format"] = "CSV"
        return ParseResult(success=True, fields=data_row, raw_message=raw, parser_id=self.parser_id, parser_version=self.version)