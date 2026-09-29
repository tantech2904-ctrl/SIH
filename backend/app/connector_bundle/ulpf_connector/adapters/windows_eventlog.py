"""Windows Event Log adapter.

Prefers pywin32's win32evtlog for a real subscription (EvtSubscribe / EvtQuery).
Falls back to polling `wevtutil qe` when pywin32 isn't installed.

Emits each event's ToXml() form — this is exactly what the backend's
windows_evtx parser expects. No binary EVTX parsing needed on the client.

Bookmark: last EventRecordID per channel, in ~/.ulpf/win_eventlog.bookmark.json.

Startup policy:
  - resume_from_bookmark=false (default): skip history, anchor to the
    current tail of every channel on startup.
  - resume_from_bookmark=true: catch up from the last delivered record ID,
    strictly bounded by max_event_age_seconds (default 15m) to prevent flooding.
  - force_anchor_now=true: overrides resume_from_bookmark, anchors to current tail.
"""
from __future__ import annotations

import json
import logging
import platform
import subprocess
import time
import re
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterator

from .base import BaseAdapter, Event

log = logging.getLogger(__name__)

_EVENT_RECORD_ID_RE = re.compile(
    r"<(?:\w+:)?EventRecordID(?:\s+[^>]*)?>\s*(\d+)\s*</(?:\w+:)?EventRecordID>",
    re.IGNORECASE,
)

_SYSTEM_TIME_RE = re.compile(
    r"TimeCreated\s+SystemTime=['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def _is_elevated() -> bool:
    """Best-effort elevated check. Returns False on non-Windows."""
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _parse_windows_system_time(ts_str: str) -> datetime | None:
    """Safely parse Windows Event SystemTime (e.g. 2026-09-27T22:02:08.0051734Z)."""
    if not ts_str:
        return None
    raw = ts_str.strip()
    try:
        # Fast path (Python 3.11+)
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        pass

    try:
        # Fallback for Python <= 3.10
        clean = raw
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        if "." in clean:
            prefix, rest = clean.split(".", 1)
            tz_part = ""
            subsec = rest
            if "+" in rest:
                subsec, tz_part = rest.split("+", 1)
                tz_part = "+" + tz_part
            elif "-" in rest:
                subsec, tz_part = rest.split("-", 1)
                tz_part = "-" + tz_part
            clean = f"{prefix}.{subsec[:6]}{tz_part}"
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def _extract_system_time(xml: str) -> datetime | None:
    """Extract and parse the event SystemTime into a timezone-aware UTC datetime."""
    match = _SYSTEM_TIME_RE.search(xml)
    if not match:
        return None
    dt = _parse_windows_system_time(match.group(1))
    if dt and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _is_event_too_old(xml: str, max_age_seconds: float = 900.0) -> bool:
    """Return True if event SystemTime is older than max_age_seconds."""
    dt = _extract_system_time(xml)
    if dt is None:
        return False
    now = datetime.now(timezone.utc)
    age = (now - dt).total_seconds()
    return age > max_age_seconds


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
        # Drop events older than this ceiling (default: 15 minutes = 900s)
        self.max_event_age_seconds: float = float(config.get("max_event_age_seconds", 900.0))
        # Strict real-time forward-only anchor: capture startup time with a 10s grace margin for clock skew
        self.start_anchor_time: datetime = datetime.now(timezone.utc) - timedelta(seconds=10)
        # Emit per-poll diagnostics. Enabled by connector.py --debug-events.
        self.debug_events: bool = bool(config.get("debug_events", False))
        self._seen_hashes: set[str] = set()

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
        started_channels: list[str] = []
        denied_channels: list[str] = []
        max_age_ms = int(self.max_event_age_seconds * 1000)

        for ch in self.channels:
            try:
                current_rid = _current_record_id(win32evtlog, ch)
                if not current_rid:
                    current_rid = _wevtutil_current_record_id(ch)

                if self.force_anchor_now or not self.resume_from_bookmark:
                    start_rid = current_rid
                    mode = "tail-now"
                    if start_rid:
                        marks[ch] = start_rid
                        self._save_bookmarks(marks)
                elif ch in marks and marks[ch] > 0:
                    start_rid = marks[ch]
                    mode = "resume-bookmark"
                else:
                    # Initial anchor: tail current head to avoid flooding hours/days of backlogs
                    start_rid = current_rid
                    mode = "tail-now"
                    if start_rid:
                        marks[ch] = start_rid
                        self._save_bookmarks(marks)

                started_channels.append(ch)
                log.info(
                    "winevt.start channel=%s mode=%s start_rid=%s max_age_s=%.0f backend=pywin32",
                    ch, mode, start_rid, self.max_event_age_seconds,
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
            "connector.watching channels=%s elevated=%s security_ok=%s backend=pywin32",
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
            for ch in started_channels:
                cursor_rid = marks.get(ch, 0)
                if cursor_rid > 0:
                    xpath = f"*[System[EventRecordID > {cursor_rid} and TimeCreated[timediff(@SystemTime) <= {max_age_ms}]]]"
                else:
                    xpath = f"*[System[TimeCreated[timediff(@SystemTime) <= {max_age_ms}]]]"

                h = None
                try:
                    h = win32evtlog.EvtQuery(
                        ch,
                        win32evtlog.EvtQueryForwardDirection,
                        xpath,
                    )
                except Exception as exc:
                    log.warning("winevt.query_failed channel=%s err=%s", ch, exc)
                    continue

                events = []
                try:
                    events = win32evtlog.EvtNext(h, self.max_events_per_poll)
                except Exception as exc:
                    err_code = getattr(exc, "winerror", None)
                    if err_code != 259 and "259" not in str(exc):
                        log.warning("winevt.next_failed channel=%s err=%s", ch, exc)
                    events = []
                finally:
                    try:
                        if hasattr(h, "close"):
                            h.close()
                        elif hasattr(win32evtlog, "EvtClose"):
                            win32evtlog.EvtClose(h)
                    except Exception:
                        pass

                if not events:
                    continue

                if self.debug_events:
                    log.debug(
                        "winevt.poll channel=%s cursor_rid=%s returned=%d",
                        ch, marks.get(ch, 0), len(events),
                    )

                for ev in events:
                    try:
                        xml = win32evtlog.EvtRender(ev, win32evtlog.EvtRenderEventXml)
                    except Exception as exc:
                        log.warning("winevt.render_failed channel=%s err=%s", ch, exc)
                        continue
                    finally:
                        try:
                            if hasattr(ev, "close"):
                                ev.close()
                            elif hasattr(win32evtlog, "EvtClose"):
                                win32evtlog.EvtClose(ev)
                        except Exception:
                            pass

                    rid = _extract_record_id(xml)
                    if rid is not None:
                        if rid <= marks.get(ch, 0):
                            continue
                    else:
                        h_val = hashlib.sha256(xml.encode("utf-8")).hexdigest()
                        if h_val in self._seen_hashes:
                            continue
                        self._seen_hashes.add(h_val)
                        if len(self._seen_hashes) > 10000:
                            self._seen_hashes.pop()

                    # Strict forward-only timestamp filter: only forward events generated at/after connector startup time
                    evt_time = _extract_system_time(xml)
                    if evt_time is not None and evt_time < self.start_anchor_time:
                        if rid is not None:
                            marks[ch] = max(marks.get(ch, 0), rid)
                            self._save_bookmarks(marks)
                        continue

                    # Stale event safety filter: drop anything older than max_event_age_seconds
                    if _is_event_too_old(xml, self.max_event_age_seconds):
                        if rid is not None:
                            marks[ch] = max(marks.get(ch, 0), rid)
                            self._save_bookmarks(marks)
                        continue

                    any_events = True
                    log.info("winevt.emit channel=%s rid=%s", ch, rid)
                    yield Event(
                        raw_bytes=xml.encode("utf-8"),
                        source=self.hostname,
                        source_type="windows_eventlog",
                        filename=f"{ch}.evtx",
                        content_type="application/xml",
                    )
                    if rid is not None:
                        marks[ch] = max(marks.get(ch, 0), rid)
                        self._save_bookmarks(marks)

            if not any_events:
                time.sleep(self.poll_seconds)

    def _stream_wevtutil(self) -> Iterator[Event]:
        marks = self._load_bookmarks()
        started_channels: list[str] = []
        max_age_ms = int(self.max_event_age_seconds * 1000)

        for ch in self.channels:
            current_rid = _wevtutil_current_record_id(ch)
            if self.force_anchor_now or not self.resume_from_bookmark:
                anchor = current_rid
                mode = "tail-now"
                if anchor:
                    marks[ch] = anchor
                    self._save_bookmarks(marks)
            elif ch not in marks or marks[ch] <= 0:
                anchor = current_rid
                mode = "tail-now"
                if anchor:
                    marks[ch] = anchor
                    self._save_bookmarks(marks)
            else:
                anchor = marks[ch]
                mode = "resume-bookmark"

            started_channels.append(ch)
            log.info(
                "winevt.start channel=%s mode=%s start_rid=%s max_age_s=%.0f backend=wevtutil",
                ch, mode, anchor, self.max_event_age_seconds,
            )

        log.info(
            "connector.watching channels=%s elevated=%s security_ok=%s backend=wevtutil",
            started_channels,
            str(_is_elevated()).lower(),
            str("Security" in started_channels).lower(),
        )

        while True:
            any_events = False
            for ch in self.channels:
                cursor_rid = marks.get(ch, 0)
                if cursor_rid > 0:
                    q = f"*[System[EventRecordID > {cursor_rid} and TimeCreated[timediff(@SystemTime) <= {max_age_ms}]]]"
                else:
                    q = f"*[System[TimeCreated[timediff(@SystemTime) <= {max_age_ms}]]]"

                cmd = [
                    "wevtutil", "qe", ch,
                    "/f:xml", "/rd:true",
                    f"/c:{self.max_events_per_poll}",
                    f"/q:{q}",
                ]
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
                # Sort ascending by record ID so cursor advances forward
                parsed = []
                for xml in events:
                    rid = _extract_record_id(xml)
                    parsed.append((rid, xml))
                parsed.sort(key=lambda item: (item[0] is None, item[0] or 0))

                for rid, xml in parsed:
                    if rid is not None:
                        if rid <= marks.get(ch, 0):
                            continue
                    else:
                        h_val = hashlib.sha256(xml.encode("utf-8")).hexdigest()
                        if h_val in self._seen_hashes:
                            continue
                        self._seen_hashes.add(h_val)
                        if len(self._seen_hashes) > 10000:
                            self._seen_hashes.pop()

                    # Strict forward-only timestamp filter: only forward events generated at/after connector startup time
                    evt_time = _extract_system_time(xml)
                    if evt_time is not None and evt_time < self.start_anchor_time:
                        if rid is not None:
                            marks[ch] = max(marks.get(ch, 0), rid)
                            self._save_bookmarks(marks)
                        continue

                    # Stale event safety filter: drop anything older than max_event_age_seconds
                    if _is_event_too_old(xml, self.max_event_age_seconds):
                        if rid is not None:
                            marks[ch] = max(marks.get(ch, 0), rid)
                            self._save_bookmarks(marks)
                        continue

                    any_events = True
                    log.info("winevt.emit channel=%s rid=%s backend=wevtutil", ch, rid)
                    yield Event(
                        raw_bytes=xml.encode("utf-8"),
                        source=self.hostname,
                        source_type="windows_eventlog",
                        filename=f"{ch}.evtx",
                        content_type="application/xml",
                    )
                    if rid is not None:
                        marks[ch] = max(marks.get(ch, 0), rid)
                        self._save_bookmarks(marks)
            if not any_events:
                time.sleep(self.poll_seconds)

    def read_once(self, limit: int = 100) -> Iterator[Event]:
        """Read last `limit` events from each channel, newest first, bounded by max_event_age."""
        max_age_ms = int(self.max_event_age_seconds * 1000)
        q = f"*[System[TimeCreated[timediff(@SystemTime) <= {max_age_ms}]]]"
        for ch in self.channels:
            cmd_ch = [
                "wevtutil", "qe", ch,
                "/f:xml", "/rd:true",
                f"/c:{limit}",
                f"/q:{q}",
            ]
            try:
                out = subprocess.run(cmd_ch, capture_output=True, text=True, timeout=20)
            except Exception as exc:
                log.error("winevt.once_failed channel=%s err=%s", ch, exc)
                continue
            for xml in _split_events(out.stdout):
                evt_time = _extract_system_time(xml)
                if evt_time is not None and evt_time < self.start_anchor_time:
                    continue
                if _is_event_too_old(xml, self.max_event_age_seconds):
                    continue
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
    match = _EVENT_RECORD_ID_RE.search(xml)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
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
            return _wevtutil_current_record_id(channel)
        xml = win32evtlog.EvtRender(events[0], win32evtlog.EvtRenderEventXml)
        rid = _extract_record_id(xml)
        return rid or _wevtutil_current_record_id(channel)
    except Exception:
        return _wevtutil_current_record_id(channel)


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