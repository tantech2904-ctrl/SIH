"""Linux systemd journal adapter.

Prefers the `systemd.journal` binding (from python-systemd) for a native
subscription. Falls back to `journalctl -f -o json` subprocess streaming
when the binding isn't installed.

Bookmark: journald cursor (`__CURSOR`), persisted to ~/.ulpf/journald.cursor.
"""
from __future__ import annotations

import json
import logging
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Iterator

from .base import BaseAdapter, Event

log = logging.getLogger(__name__)


# journald PRIORITY is syslog-standard (0 = EMERG = worst, 7 = DEBUG = least).
# The backend's _parse_severity() treats a bare number as CEF severity
# (higher = worse), which is the opposite convention. We translate here so
# no vendor-specific logic leaks into cse.py.
_JOURNALD_PRIORITY_TO_SEVERITY = {
    "0": "CRITICAL",  # EMERG
    "1": "CRITICAL",  # ALERT
    "2": "CRITICAL",  # CRIT
    "3": "HIGH",      # ERR
    "4": "MEDIUM",    # WARNING
    "5": "LOW",       # NOTICE
    "6": "INFO",      # INFO
    "7": "INFO",      # DEBUG
}


def _translate_priority(payload: dict) -> dict:
    pri = payload.pop("PRIORITY", None)
    if pri is not None:
        payload["severity"] = _JOURNALD_PRIORITY_TO_SEVERITY.get(str(pri), "INFO")
    return payload


class LinuxJournaldAdapter(BaseAdapter):
    name = "linux_journald"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.units: list[str] = config.get("units") or []
        self.priority_max: int = int(config.get("priority_max", 6))
        self.cursor_file = Path(
            config.get("bookmark_file", "~/.ulpf/journald.cursor")
        ).expanduser()
        self.cursor_file.parent.mkdir(parents=True, exist_ok=True)
        self.hostname = platform.node() or "unknown-linux-host"

    def is_available(self) -> bool:
        if platform.system() != "Linux":
            return False
        if not shutil.which("journalctl"):
            return False
        return True

    def _load_cursor(self) -> str | None:
        if not self.cursor_file.exists():
            return None
        try:
            return self.cursor_file.read_text().strip() or None
        except Exception:
            return None

    def _save_cursor(self, cursor: str) -> None:
        try:
            self.cursor_file.write_text(cursor)
        except Exception as exc:
            log.warning("journald.cursor_save_failed err=%s", exc)

    def stream(self) -> Iterator[Event]:
        try:
            from systemd import journal  # type: ignore
            yield from self._stream_native(journal)
            return
        except ImportError:
            pass
        yield from self._stream_subprocess()

    def _stream_native(self, journal) -> Iterator[Event]:
        reader = journal.Reader()
        reader.this_boot()
        for u in self.units:
            reader.add_match(_SYSTEMD_UNIT=u)
        if hasattr(reader, "log_level"):
            reader.log_level(self.priority_max)

        cursor = self._load_cursor()
        if cursor:
            try:
                reader.seek_cursor(cursor)
                reader.get_next()
            except Exception:
                pass

        while True:
            if reader.process() != journal.APPEND:
                time.sleep(0.5)
                continue
            for entry in reader:
                try:
                    payload = {k: _json_safe(v) for k, v in entry.items()}
                    payload = _translate_priority(payload)
                    yield Event(
                        raw_bytes=json.dumps(payload, default=str).encode("utf-8"),
                        source=self.hostname,
                        source_type="journald",
                        filename="system.journal",
                        content_type="application/json",
                    )
                    cur = entry.get("__CURSOR")
                    if cur:
                        self._save_cursor(cur)
                except Exception as exc:
                    log.error("journald.native_emit_failed err=%s", exc)

    def _stream_subprocess(self) -> Iterator[Event]:
        cmd = ["journalctl", "-f", "-o", "json", "-p", str(self.priority_max)]
        for u in self.units:
            cmd.extend(["-u", u])

        cursor = self._load_cursor()
        if cursor:
            cmd.extend(["--after-cursor", cursor])

        log.info("journald.streaming cmd=%s", " ".join(cmd))
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
        )
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    cur = entry.get("__CURSOR")
                    if cur:
                        self._save_cursor(cur)
                    entry = _translate_priority(entry)
                    line = json.dumps(entry, default=str)
                except Exception:
                    pass
                yield Event(
                    raw_bytes=line.encode("utf-8"),
                    source=self.hostname,
                    source_type="journald",
                    filename="system.journal",
                    content_type="application/json",
                )
        finally:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                pass

    def read_once(self, limit: int = 100) -> Iterator[Event]:
        cmd = ["journalctl", "-o", "json", "-n", str(limit), "-p", str(self.priority_max)]
        for u in self.units:
            cmd.extend(["-u", u])
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        except Exception as exc:
            log.error("journald.once_failed err=%s", exc)
            return
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entry = _translate_priority(entry)
                line = json.dumps(entry, default=str)
            except Exception:
                pass
            yield Event(
                raw_bytes=line.encode("utf-8"),
                source=self.hostname,
                source_type="journald",
                filename="system.journal",
                content_type="application/json",
            )


def _json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)