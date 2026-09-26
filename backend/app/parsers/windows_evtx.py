from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import xmltodict

from app.parsers.base import BaseParser, DetectionResult, ParseResult

# python-evtx is an optional dependency. It requires a C compiler to
# install on Python 3.12+. If it's missing, binary .evtx ingestion is
# unavailable, but XML-based EVTX parsing still works (see below).
try:
    from Evtx.Evtx import Evtx  # type: ignore  # noqa: F401
    _EVTX_AVAILABLE = True
except ImportError:
    Evtx = None  # type: ignore
    _EVTX_AVAILABLE = False


def extract_windows_event_records(raw_bytes: bytes) -> list[str]:
    """Convert native Windows EVTX/EVT binary data into XML event records.

    Raises RuntimeError if binary input is given but python-evtx is not
    installed.
    """
    if not raw_bytes:
        return []

    # If the payload is already plain XML text, leave it to the existing XML pipeline.
    if raw_bytes.lstrip().startswith(b"<"):
        return [raw_bytes.decode("utf-8", errors="replace")]

    # Binary .evtx requires the optional python-evtx package.
    if not _EVTX_AVAILABLE:
        raise RuntimeError(
            "Binary .evtx ingestion requires the optional 'python-evtx' "
            "package. Install it with:  pip install python-evtx"
        )

    records: list[str] = []
    try:
        with tempfile.NamedTemporaryFile(suffix=".evtx", delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        try:
            with Evtx(tmp_path) as evtx:
                for rec in evtx.records():
                    xml_text = rec.xml()
                    if xml_text and xml_text.strip():
                        records.append(xml_text)
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        return []

    return records


class WindowsEventLogParser(BaseParser):
    parser_id = "windows_evtx"
    name = "Windows Event Log"
    vendor = "Microsoft"
    format_name = "EVTX"
    version = "1.0.0"

    def detect(self, raw: str, *, filename: str | None = None) -> DetectionResult:
        text = (raw or "").strip()
        lname = (filename or "").lower()

        if lname.endswith(".evtx") or lname.endswith(".evt"):
            return DetectionResult(
                "EVTX",
                0.99,
                ["Filename indicates native Windows event log format"],
            )

        if "<Event" in text and "<System" in text and ("<EventData" in text or "<EventID>" in text):
            return DetectionResult(
                "EVTX",
                0.85,
                ["Windows Event XML structure detected"],
            )

        return DetectionResult("EVTX", 0.0, [])

    def parse(self, raw: str | bytes) -> ParseResult:
        if isinstance(raw, (bytes, bytearray)):
            payload = bytes(raw)
            if payload.lstrip().startswith(b"<"):
                text = payload.decode("utf-8", errors="replace")
            else:
                try:
                    records = extract_windows_event_records(payload)
                except RuntimeError as e:
                    return ParseResult(
                        success=False,
                        parser_id=self.parser_id,
                        parser_version=self.version,
                        errors=[str(e)],
                    )
                if not records:
                    return ParseResult(
                        success=False,
                        parser_id=self.parser_id,
                        parser_version=self.version,
                        errors=["No Windows Event Log records could be extracted from the payload"],
                    )
                text = records[0]
        else:
            text = (raw or "").strip()

        if not text:
            return ParseResult(
                success=False,
                parser_id=self.parser_id,
                parser_version=self.version,
                errors=["Empty Windows Event Log payload"],
            )

        try:
            obj = xmltodict.parse(text)
        except Exception as e:
            return ParseResult(
                success=False,
                parser_id=self.parser_id,
                parser_version=self.version,
                errors=[f"Windows Event XML parse error: {e}"],
            )

        event = obj.get("Event") if isinstance(obj, dict) else None
        if not isinstance(event, dict):
            return ParseResult(
                success=False,
                parser_id=self.parser_id,
                parser_version=self.version,
                errors=["Windows Event XML did not contain an Event root node"],
            )

        system = event.get("System") or {}
        event_data = event.get("EventData") or {}

        fields: dict[str, Any] = {
            "format": "EVTX",
            "raw_xml": text,
            "channel": system.get("Channel"),
            "event_id": system.get("EventID"),
            "level": system.get("Level"),
            "task": system.get("Task"),
            "opcode": system.get("Opcode"),
            "provider_name": (system.get("Provider") or {}).get("@Name"),
            "provider_guid": (system.get("Provider") or {}).get("@Guid"),
            "computer": system.get("Computer"),
            "time_created": (system.get("TimeCreated") or {}).get("@SystemTime"),
            "record_id": system.get("EventRecordID"),
            "keywords": system.get("Keywords"),
        }

        event_data_payload = _event_data_fields(event_data)
        fields.update(event_data_payload)

        # Best-effort message: prefer the rendered <RenderingInfo><Message>,
        # fall back to EventData['message'], then synthesize a short summary
        # from the top EventData fields so the CSE and UI always have text.
        event_message = (
            (event.get("RenderingInfo") or {}).get("Message")
            or event_data_payload.get("message")
        )
        if event_message:
            fields["message"] = str(event_message)[:1024]
        elif event_data_payload:
            parts = [
                f"{k}={v}"
                for k, v in event_data_payload.items()
                if v and k != "event_data"
            ][:6]
            if parts:
                fields["message"] = " ".join(parts)[:1024]

        return ParseResult(
            success=True,
            fields=fields,
            raw_message=text,
            parser_id=self.parser_id,
            parser_version=self.version,
            vendor="Microsoft",
            product="Windows Event Log",
        )


def _event_data_fields(event_data: Any) -> dict[str, Any]:
    if not isinstance(event_data, dict):
        return {}

    data_nodes = event_data.get("Data", [])
    if isinstance(data_nodes, dict):
        data_nodes = [data_nodes]

    flattened: dict[str, Any] = {}
    for item in data_nodes:
        if isinstance(item, dict):
            name = item.get("@Name") or item.get("name")
            if name:
                flattened[name] = item.get("#text") or item.get("text") or item.get("value")

    if flattened:
        flattened["event_data"] = flattened

    return flattened