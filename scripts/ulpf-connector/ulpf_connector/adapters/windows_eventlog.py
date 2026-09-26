"""Windows Event Log adapter.

Prefers pywin32's win32evtlog for a real subscription (EvtSubscribe).
Falls back to polling `wevtutil qe` when pywin32 isn't installed.

Emits each event's ToXml() form — this is exactly what the backend's
windows_evtx parser expects. No binary EVTX parsing needed on the client.

Bookmark: last EventRecordID per channel, in
~/.ulpf/win_eventlog.bookmark.json.

Startup policy:
  - resume_from_bookmark=false (default): skip history, anchor to the
    current tail of every channel on startup.
  - resume_from_bookmark=true: catch up from the last delivered record ID.
  - force_anchor_now=true: overrides resume_from_bookmark for one run.
"""
from __future__ import annotations

import json
import logging
import platform
import subprocess
import time
from pathlib import Path
from typing import Iterator

from .base import BaseAdapter, Event

log = logging.getLogger(__name__)


def _is_elevated() -> bool:
    """Best-effort elevated check. Returns False on non-Windows."""
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class WindowsEventLogAdapter(BaseAdapter):
    name = "windows_eventlog"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.channels: list[str] = config.get("channels") or ["Security", "System", "Application"]
        self.filter_xpath: str = config.get("filter_xpath", "*")
        self.poll_seconds: float = float(config.get("poll_seconds", 2.0))
        self.max_events_per_poll: int = int(config.get("max_events_per_poll", 200))
        self.bookmark_file = Path(
            config.get("bookmark_file", "~/.ulpf/win_eventlog.bookmark.json")
        ).expanduser()
        self.bookmark_file.parent.mkdir(parents=True, exist_ok=True)
        self.hostname = platform.node() or "unknown-windows-host"
        self.resume_from_bookmark: bool = bool(config.get("resume_from_bookmark", False))
        self.force_anchor_now: bool = bool(config.get("force_anchor_now", False))
        # Emit per-poll diagnostics. Enabled by connector.py --debug-events.
        self.debug_events: bool = bool(config.get("debug_events", False))

    def is_available(self) -> bool:
        return platform.system() == "Windows"

    # ------------------------------------------------------------- bookmarks

    def _load_bookmarks(self) -> dict[str, int]:
        if not self.bookmark_file.exists():
            return {}
        try:
            return json.loads(self.bookmark_file.read_text())
        except Exception:
            return {}

    def _save_bookmarks(self, marks: dict[str, int]) -> None:
        try:
            self.bookmark_file.write_text(json.dumps(marks, indent=2))
        except Exception as exc:
            log.warning("winevt.bookmark_save_failed err=%s", exc)

    # ------------------------------------------------------------------ stream

    def stream(self) -> Iterator[Event]:
        try:
            import win32evtlog  # type: ignore  # noqa: F401
            yield from self._stream_pywin32()
            return
        except ImportError:
            log.info("winevt.pywin32_unavailable, using wevtutil fallback")
        yield from self._stream_wevtutil()

    def _stream_pywin32(self) -> Iterator[Event]:
        import win32evtlog  # type: ignore
        import win32evtlogutil  # type: ignore  # noqa: F401

        marks = self._load_bookmarks()
        handles = {}
        started_channels: list[str] = []
        denied_channels: list[str] = []

        for ch in self.channels:
            try:
                if self.force_anchor_now:
                    start_rid = _current_record_id(win32evtlog, ch)
                    mode = "forced-skip"
                    if start_rid:
                        marks[ch] = start_rid
                        self._save_bookmarks(marks)
                elif self.resume_from_bookmark:
                    start_rid = marks.get(ch, 0)
                    mode = "resume"
                else:
                    start_rid = _current_record_id(win32evtlog, ch)
                    mode = "skip-history"
                    if start_rid:
                        marks[ch] = start_rid
                        self._save_bookmarks(marks)

                xpath = (
                    f"*[System[EventRecordID > {start_rid}]]"
                    if start_rid and start_rid > 0
                    else self.filter_xpath
                )
                h = win32evtlog.EvtQuery(
                    ch,
                    win32evtlog.EvtQueryForwardDirection,
                    xpath,
                )
                handles[ch] = h
                started_channels.append(ch)
                log.info(
                    "winevt.start channel=%s mode=%s start_rid=%s xpath=%s",
                    ch, mode, start_rid, xpath,
                )
            except Exception as exc:
                msg = str(exc)
                if "Access is denied" in msg or "(5," in msg:
                    denied_channels.append(ch)
                log.error("winevt.subscribe_failed channel=%s err=%s", ch, exc)

        # Startup summary — one line at a glance.
        elevated = _is_elevated()
        security_ok = "Security" not in denied_channels and (
            "Security" in started_channels
        )
        log.info(
            "connector.watching channels=%s elevated=%s security_ok=%s",
            started_channels, str(elevated).lower(), str(security_ok).lower(),
        )
        if denied_channels:
            log.warning(
                "connector.channels_denied denied=%s hint=%s",
                denied_channels,
                "Run as Administrator (Security channel requires elevation).",
            )

        while True:
            any_events = False
            for ch, h in handles.items():
                try:
                    events = win32evtlog.EvtNext(h, self.max_events_per_poll)
                except Exception as exc:
                    log.warning("winevt.next_failed channel=%s err=%s", ch, exc)
                    continue
                if self.debug_events:
                    log.debug(
                        "winevt.poll channel=%s cursor_rid=%s returned=%d",
                        ch, marks.get(ch, 0), len(events or []),
                    )
                mark = marks.get(ch, 0)
                for ev in events:
                    any_events = True
                    xml = win32evtlog.EvtRender(ev, win32evtlog.EvtRenderEventXml)
                    rid = _extract_record_id(xml)
                    if rid is not None and rid <= mark:
                        continue
                    if self.debug_events:
                        log.debug("winevt.emit channel=%s rid=%s", ch, rid)
                    yield Event(
                        raw_bytes=xml.encode("utf-8"),
                        source=self.hostname,
                        source_type="windows_eventlog",
                        filename=f"{ch}.evtx",
                        content_type="application/xml",
                    )
                    if rid is not None:
                        mark = rid
                        marks[ch] = rid
                        self._save_bookmarks(marks)
            if not any_events:
                time.sleep(self.poll_seconds)

    def _stream_wevtutil(self) -> Iterator[Event]:
        marks = self._load_bookmarks()
        started_channels: list[str] = []
        for ch in self.channels:
            if self.force_anchor_now or not self.resume_from_bookmark:
                anchor = _wevtutil_current_record_id(ch)
                if anchor:
                    marks[ch] = anchor
                    self._save_bookmarks(marks)
                    log.info(
                        "winevt.start channel=%s mode=%s start_rid=%s backend=wevtutil",
                        ch,
                        "forced-skip" if self.force_anchor_now else "skip-history",
                        anchor,
                    )
            started_channels.append(ch)

        log.info(
            "connector.watching channels=%s elevated=%s security_ok=%s backend=wevtutil",
            started_channels,
            str(_is_elevated()).lower(),
            str("Security" in started_channels).lower(),
        )

        while True:
            any_events = False
            for ch in self.channels:
                cmd = [
                    "wevtutil", "qe", ch,
                    "/f:xml", "/rd:true",
                    f"/c:{self.max_events_per_poll}",
                ]
                if self.filter_xpath and self.filter_xpath != "*":
                    cmd.append(f"/q:{self.filter_xpath}")
                try:
                    out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                except Exception as exc:
                    log.warning("winevt.wevtutil_failed channel=%s err=%s", ch, exc)
                    continue
                events = _split_events(out.stdout)
                if self.debug_events:
                    log.debug(
                        "winevt.poll channel=%s cursor_rid=%s returned=%d backend=wevtutil",
                        ch, marks.get(ch, 0), len(events),
                    )
                for xml in events:
                    rid = _extract_record_id(xml)
                    if rid is not None and rid <= marks.get(ch, 0):
                        continue
                    any_events = True
                    yield Event(
                        raw_bytes=xml.encode("utf-8"),
                        source=self.hostname,
                        source_type="windows_eventlog",
                        filename=f"{ch}.evtx",
                        content_type="application/xml",
                    )
                    if rid is not None:
                        marks[ch] = rid
                        self._save_bookmarks(marks)
            if not any_events:
                time.sleep(self.poll_seconds)

    def read_once(self, limit: int = 100) -> Iterator[Event]:
        """Read last `limit` events from each channel, newest first, then stop."""
        for ch in self.channels:
            cmd_ch = ["wevtutil", "qe", ch, "/f:xml", "/rd:true", f"/c:{limit}"]
            try:
                out = subprocess.run(cmd_ch, capture_output=True, text=True, timeout=20)
            except Exception as exc:
                log.error("winevt.once_failed channel=%s err=%s", ch, exc)
                continue
            for xml in _split_events(out.stdout):
                yield Event(
                    raw_bytes=xml.encode("utf-8"),
                    source=self.hostname,
                    source_type="windows_eventlog",
                    filename=f"{ch}.evtx",
                    content_type="application/xml",
                )


# -------------------------------------------------------------------- helpers

def _split_events(xml_blob: str) -> list[str]:
    """Split concatenated <Event>…</Event> XML documents emitted by wevtutil."""
    events: list[str] = []
    depth = 0
    start: int | None = None
    i = 0
    n = len(xml_blob)
    while i < n:
        if xml_blob.startswith("<Event", i):
            j = i + 1
            if j < n and xml_blob[j] == "E":
                if start is None:
                    start = i
                    depth = 1
                    i += 6
                    continue
        elif xml_blob.startswith("</Event>", i):
            depth -= 1
            if depth == 0 and start is not None:
                events.append(xml_blob[start : i + len("</Event>")])
                start = None
            i += len("</Event>")
            continue
        i += 1
    return events


def _extract_record_id(xml: str) -> int | None:
    """Extract <EventRecordID>NNN</EventRecordID> from a Windows event XML."""
    key_open = "<EventRecordID>"
    key_close = "</EventRecordID>"
    i = xml.find(key_open)
    if i < 0:
        return None
    j = xml.find(key_close, i)
    if j < 0:
        return None
    raw = xml[i + len(key_open) : j].strip()
    try:
        return int(raw)
    except Exception:
        return None


def _current_record_id(win32evtlog, channel: str) -> int:
    """Return the highest EventRecordID currently in the channel."""
    try:
        h = win32evtlog.EvtQuery(
            channel,
            win32evtlog.EvtQueryReverseDirection,
            "*",
        )
        events = win32evtlog.EvtNext(h, 1)
        if not events:
            return 0
        xml = win32evtlog.EvtRender(events[0], win32evtlog.EvtRenderEventXml)
        rid = _extract_record_id(xml)
        return rid or 0
    except Exception:
        return 0


def _wevtutil_current_record_id(channel: str) -> int:
    """Return the highest EventRecordID in `channel` via wevtutil."""
    try:
        out = subprocess.run(
            ["wevtutil", "qe", channel, "/f:xml", "/rd:true", "/c:1"],
            capture_output=True, text=True, timeout=20,
        )
    except Exception:
        return 0
    events = _split_events(out.stdout)
    if not events:
        return 0
    return _extract_record_id(events[0]) or 0