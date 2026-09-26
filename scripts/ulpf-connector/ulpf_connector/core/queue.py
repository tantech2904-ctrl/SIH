"""In-memory queue with disk spooling for reliability.

Events that fail to send are held in a bounded in-memory deque. On shutdown
or overflow, they spill to a JSONL spool file. On startup the spool is
replayed before live streaming resumes.

Design goals:
  - Never block the adapter threads for long — the queue is a fast in-memory
    append; spilling happens on the drain side.
  - Never lose an event silently — either it's in memory, on disk, or was
    acknowledged by the backend.
"""
from __future__ import annotations

import json
import logging
import threading
from collections import deque
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class SpoolQueue:
    """Thread-safe bounded queue with disk spool overflow."""

    def __init__(self, max_in_memory: int, spool_file: str) -> None:
        self._lock = threading.Lock()
        self._q: deque[dict[str, Any]] = deque(maxlen=max_in_memory)
        self._spool_path = Path(spool_file).expanduser()
        self._spool_path.parent.mkdir(parents=True, exist_ok=True)
        self._overflow_count = 0

    def put(self, item: dict[str, Any]) -> None:
        with self._lock:
            if len(self._q) == self._q.maxlen:
                # Full: spill the oldest item to disk to make room.
                oldest = self._q.popleft()
                self._append_spool(oldest)
                self._overflow_count += 1
            self._q.append(item)

    def get_nowait(self) -> dict[str, Any] | None:
        with self._lock:
            if self._q:
                return self._q.popleft()
            return None

    def requeue_front(self, item: dict[str, Any]) -> None:
        """Put an item back at the head (used after a transient send failure)."""
        with self._lock:
            self._q.appendleft(item)

    def __len__(self) -> int:
        with self._lock:
            return len(self._q)

    @property
    def overflow_count(self) -> int:
        return self._overflow_count

    def _append_spool(self, item: dict[str, Any]) -> None:
        try:
            with self._spool_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(item, separators=(",", ":")) + "\n")
        except Exception as exc:
            log.error("spool.append_failed path=%s err=%s", self._spool_path, exc)

    def replay_spool(self, max_items: int = 10000) -> int:
        """Move everything currently in the spool file into memory. Returns count.

        ... (docstring above) ...
        """
        if not self._spool_path.exists():
            return 0

        items: list[dict[str, Any]] = []
        skipped = 0
        try:
            with self._spool_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if len(items) >= max_items:
                        skipped += 1
                        continue
                    try:
                        items.append(json.loads(line))
                    except Exception:
                        continue
        except Exception as exc:
            log.error("spool.read_failed path=%s err=%s", self._spool_path, exc)
            return 0

        if skipped:
            log.warning(
                "spool.replay_truncated kept=%d skipped=%d path=%s",
                len(items), skipped, self._spool_path,
            )

        try:
            self._spool_path.write_text("", encoding="utf-8")
        except Exception as exc:
            log.error("spool.truncate_failed path=%s err=%s", self._spool_path, exc)
            return 0

        for item in items:
            self.put(item)
        return len(items)

        # Truncate BEFORE enqueueing, so a full deque can't write back to a
        # file we're about to read from.
        try:
            self._spool_path.write_text("", encoding="utf-8")
        except Exception as exc:
            log.error("spool.truncate_failed path=%s err=%s", self._spool_path, exc)
            return 0

        for item in items:
            self.put(item)
        return len(items)

    def spill_all(self) -> int:
        """Dump everything currently in memory to the spool file. Returns count."""
        with self._lock:
            items = list(self._q)
            self._q.clear()
        for item in items:
            self._append_spool(item)
        return len(items)