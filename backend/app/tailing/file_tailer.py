"""File tail ingestor.

Watches a fixed list of log files and ingests new lines through the
existing ingest_event() pipeline.

Design notes:
- One asyncio task per configured path is NOT used; instead, a single
  loop iterates over all paths on each poll tick. This keeps the
  concurrency model simple and avoids N task lifecycles.
- Offsets are tracked per path in memory. On restart, offsets reset;
  LOG_TAIL_FROM_START controls whether we re-read the file from the
  beginning or seek to the end on first encounter.
- Rotation is detected via size-shrink: if a file's current size is
  smaller than our last-known offset, we assume it was rotated or
  truncated and re-read from the beginning.
- Missing files are logged at debug level and retried every poll.
  They are never a fatal condition — operators commonly drop files
  into the watch directory while the container is running.
- Oversized lines are dropped with a warning, matching the UDP
  listener's MAX_EVENT_BYTES behavior. We never truncate silently.
- Audit entries use actor="system:file_tail".
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.audit_service import record_audit
from app.services.ingest_service import ingest_event, dispatch_enrichment_async

log = get_logger(__name__)

_SOURCE_TYPE = "file_tail"
_CONTENT_TYPE = "text/plain"
_AUDIT_ACTOR = "system:file_tail"


@dataclass
class _FileState:
    """Per-file read cursor."""
    offset: int = 0
    initialized: bool = False
    missing_logged: bool = False


@dataclass
class FileTailer:
    """Watches a list of log files and ingests new lines.

    Not thread-safe. All access happens from a single asyncio task.
    """
    paths: list[str] = field(default_factory=list)
    poll_seconds: float = 1.0
    from_start: bool = False

    _states: dict[str, _FileState] = field(default_factory=dict)
    _task: Optional[asyncio.Task] = None
    _stopped: bool = False

    async def start(self) -> None:
        self._stopped = False
        # Initialize states
        for p in self.paths:
            if p not in self._states:
                self._states[p] = _FileState()
        log.info(
            "file_tail.starting",
            paths=self.paths,
            poll_seconds=self.poll_seconds,
            from_start=self.from_start,
        )
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        log.info("file_tail.stopped")

    # ---- main loop -------------------------------------------------------

    async def _run(self) -> None:
        while not self._stopped:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.exception("file_tail.poll_failed", error=str(e)[:500])
            try:
                await asyncio.sleep(self.poll_seconds)
            except asyncio.CancelledError:
                raise

    async def _poll_once(self) -> None:
        """Run one poll iteration across all paths.

        Synchronous DB work is offloaded to the default executor so the
        event loop is not blocked by DB round-trips.
        """
        loop = asyncio.get_running_loop()
        for path in self.paths:
            try:
                await loop.run_in_executor(None, self._process_file, path)
            except Exception as e:
                log.exception(
                    "file_tail.process_file_failed",
                    path=path,
                    error=str(e)[:500],
                )

    # ---- per-file processing --------------------------------------------

    def _process_file(self, path: str) -> None:
        state = self._states.setdefault(path, _FileState())
        p = Path(path)

        if not p.exists():
            if not state.missing_logged:
                log.debug("file_tail.file_missing", path=path)
                state.missing_logged = True
            return
        state.missing_logged = False

        try:
            size = p.stat().st_size
        except OSError as e:
            log.warning("file_tail.stat_failed", path=path, error=str(e)[:200])
            return

        # First-time initialization
        if not state.initialized:
            if self.from_start:
                state.offset = 0
            else:
                # Seek to end — only new lines are ingested.
                state.offset = size
            state.initialized = True
            log.info("file_tail.initialized", path=path, offset=state.offset)
            return

        # Rotation / truncation detection
        if size < state.offset:
            log.info(
                "file_tail.rotation_detected",
                path=path,
                previous_offset=state.offset,
                new_size=size,
            )
            state.offset = 0

        if size == state.offset:
            return  # nothing new

        # Read from offset to end
        try:
            with open(path, "rb") as f:
                f.seek(state.offset)
                chunk = f.read()
                state.offset = f.tell()
        except OSError as e:
            log.warning("file_tail.read_failed", path=path, error=str(e)[:200])
            return

        # Split into lines; keep the trailing partial line un-processed
        # until the next poll (a file writer may be mid-write).
        # We only process complete lines (ending with \n).
        text = chunk.decode("utf-8", errors="replace")
        if "\n" not in text:
            # No complete line yet. Roll back offset so we re-read from
            # the same position next time.
            state.offset -= len(chunk)
            return

        lines = text.split("\n")
        # Last element is the partial trailing line (or empty). Roll
        # back offset by its length so we re-read it once it's complete.
        trailing = lines.pop()  # last element after split
        if trailing:
            state.offset -= len(trailing.encode("utf-8"))

        if not lines:
            return

        self._ingest_lines(path, lines)

    def _ingest_lines(self, path: str, lines: list[str]) -> None:
        db = SessionLocal()
        ingested_ids: list[str] = []
        try:
            for raw_line in lines:
                line = raw_line.rstrip("\r")
                if not line.strip():
                    continue
                raw_bytes = line.encode("utf-8")
                if len(raw_bytes) > settings.MAX_EVENT_BYTES:
                    log.warning(
                        "file_tail.oversized_line_dropped",
                        path=path,
                        size=len(raw_bytes),
                        max=settings.MAX_EVENT_BYTES,
                    )
                    continue
                try:
                    event = ingest_event(
                        db,
                        raw_bytes=raw_bytes,
                        source=f"file:{path}",
                        source_type=_SOURCE_TYPE,
                        filename=os.path.basename(path),
                        content_type=_CONTENT_TYPE,
                    )
                    ingested_ids.append(event.event_id)
                except Exception as e:
                    log.warning(
                        "file_tail.ingest_line_failed",
                        path=path,
                        error=str(e)[:200],
                    )
                    # Continue with the next line — one bad line must not
                    # stop the tail.

            if ingested_ids:
                record_audit(
                    db,
                    actor=_AUDIT_ACTOR,
                    action="INGEST_FILE_TAIL",
                    resource="file",
                    resource_id=path,
                    new_state={
                        "line_count": len(ingested_ids),
                        "event_ids": ingested_ids[:20],  # cap for audit size
                    },
                )
                db.commit()
                log.info(
                    "file_tail.ingested",
                    path=path,
                    count=len(ingested_ids),
                )
                # Dispatch enrichment outside the try that might swallow
                # exceptions — but dispatch is itself best-effort.
                dispatch_enrichment_async(ingested_ids)
        except Exception as e:
            db.rollback()
            log.exception("file_tail.ingest_batch_failed", path=path, error=str(e)[:500])
        finally:
            db.close()