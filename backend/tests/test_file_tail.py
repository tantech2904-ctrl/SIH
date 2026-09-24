"""Tests for the file tail ingestor.

Covers: initial seek-to-end, incremental reads, rotation/truncation,
oversized line handling, blank line skipping, and missing file recovery.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.event import Event
from app.tailing.file_tailer import FileTailer


def _count_events_for_source(source: str) -> int:
    s = SessionLocal()
    try:
        return s.query(Event).filter(Event.source == source).count()
    finally:
        s.close()


def test_tail_seeks_to_end_by_default(tmp_path):
    """First poll should not re-ingest pre-existing lines."""
    log_file = tmp_path / "auth.log"
    log_file.write_text(
        "<34>1 2026-01-15T10:00:00Z host app 1 OLD - pre-existing line\n"
    )

    tailer = FileTailer(paths=[str(log_file)], poll_seconds=0.1, from_start=False)
    tailer._process_file(str(log_file))  # first poll: initialize
    assert _count_events_for_source(f"file:{log_file}") == 0

    # Append a new line; next poll should ingest it.
    with log_file.open("a") as f:
        f.write("<34>1 2026-01-15T10:00:01Z host app 2 NEW - fresh line\n")

    tailer._process_file(str(log_file))
    assert _count_events_for_source(f"file:{log_file}") == 1


def test_tail_from_start_ingests_existing_lines(tmp_path):
    """from_start=True should ingest everything on first poll."""
    log_file = tmp_path / "auth.log"
    log_file.write_text(
        "<34>1 2026-01-15T10:00:00Z host app 1 A - first\n"
        "<34>1 2026-01-15T10:00:01Z host app 2 B - second\n"
    )

    tailer = FileTailer(paths=[str(log_file)], poll_seconds=0.1, from_start=True)
    # First poll initializes offset to 0. Second poll reads lines.
    tailer._process_file(str(log_file))
    tailer._process_file(str(log_file))
    assert _count_events_for_source(f"file:{log_file}") == 2


def test_tail_handles_rotation_by_size_shrink(tmp_path):
    """If the file shrinks, we assume rotation and re-read from start."""
    log_file = tmp_path / "auth.log"
    log_file.write_text(
        "<34>1 2026-01-15T10:00:00Z host app 1 A - first\n"
    )

    tailer = FileTailer(paths=[str(log_file)], poll_seconds=0.1, from_start=False)
    # Initialize: seek to end, no ingest.
    tailer._process_file(str(log_file))

    # Truncate (simulate rotation to a new, smaller file).
    log_file.write_text(
        "<34>1 2026-01-15T10:05:00Z host app 99 ROT - post rotation\n"
    )

    tailer._process_file(str(log_file))
    # The truncated file's content should be ingested.
    assert _count_events_for_source(f"file:{log_file}") >= 1


def test_oversized_line_is_dropped(tmp_path, monkeypatch):
    """Lines exceeding MAX_EVENT_BYTES are dropped, not truncated."""
    monkeypatch.setattr(settings, "MAX_EVENT_BYTES", 64, raising=False)

    log_file = tmp_path / "auth.log"
    log_file.write_text("x" * 200 + "\n")

    tailer = FileTailer(paths=[str(log_file)], poll_seconds=0.1, from_start=True)
    tailer._process_file(str(log_file))
    tailer._process_file(str(log_file))
    assert _count_events_for_source(f"file:{log_file}") == 0


def test_blank_lines_are_skipped(tmp_path):
    """Blank lines produce no events."""
    log_file = tmp_path / "auth.log"
    log_file.write_text(
        "\n"
        "<34>1 2026-01-15T10:00:00Z host app 1 A - real\n"
        "   \n"
    )

    tailer = FileTailer(paths=[str(log_file)], poll_seconds=0.1, from_start=True)
    tailer._process_file(str(log_file))
    tailer._process_file(str(log_file))
    assert _count_events_for_source(f"file:{log_file}") == 1


def test_missing_file_is_not_fatal(tmp_path):
    """A path that doesn't exist should not raise."""
    missing = tmp_path / "does_not_exist.log"
    tailer = FileTailer(paths=[str(missing)], poll_seconds=0.1, from_start=False)
    # Should return quietly without raising.
    tailer._process_file(str(missing))
    assert _count_events_for_source(f"file:{missing}") == 0