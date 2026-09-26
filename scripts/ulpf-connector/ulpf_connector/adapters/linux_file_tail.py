"""Linux file-tail adapter.

Tails one or more files, watching for new content, handling rotation
(size shrink → re-seek to 0). This is the host-side counterpart to the
backend's in-container LOG_TAIL_ENABLED mode: it can see files that
aren't bind-mounted into the backend container.

Bookmarks are stored per-file under ~/.ulpf/file_tail.<hash>.json.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import time
from pathlib import Path
from typing import Iterator

from .base import BaseAdapter, Event

log = logging.getLogger(__name__)


DEFAULT_LINUX_PATHS = [
    "/var/log/auth.log",    # Debian/Ubuntu family
    "/var/log/secure",      # RHEL family
    "/var/log/syslog",
    "/var/log/messages",
]


class LinuxFileTailAdapter(BaseAdapter):
    name = "linux_file_tail"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.paths: list[str] = config.get("paths") or self._default_paths()
        self.from_start: bool = bool(config.get("from_start", False))
        self.poll_seconds: float = float(config.get("poll_seconds", 1.0))
        self.bookmark_dir = Path(
            config.get("bookmark_dir", "~/.ulpf")
        ).expanduser()
        self.bookmark_dir.mkdir(parents=True, exist_ok=True)
        self.max_line_bytes = int(config.get("max_line_bytes", 1_048_576))
        self.hostname = platform.node() or "unknown-linux-host"

    def _default_paths(self) -> list[str]:
        return [p for p in DEFAULT_LINUX_PATHS if Path(p).exists()]

    def is_available(self) -> bool:
        return platform.system() == "Linux" and any(Path(p).exists() for p in self.paths)

    # ---------------------------------------------------------------- bookmark

    def _bookmark_path(self, file_path: str) -> Path:
        h = hashlib.sha1(file_path.encode("utf-8")).hexdigest()[:12]
        return self.bookmark_dir / f"file_tail.{h}.json"

    def _load_offset(self, file_path: str) -> int:
        bp = self._bookmark_path(file_path)
        if not bp.exists():
            return 0
        try:
            data = json.loads(bp.read_text())
            return int(data.get("offset", 0))
        except Exception:
            return 0

    def _save_offset(self, file_path: str, offset: int) -> None:
        bp = self._bookmark_path(file_path)
        try:
            bp.write_text(json.dumps({"path": file_path, "offset": offset}))
        except Exception as exc:
            log.warning("file_tail.bookmark_save_failed path=%s err=%s", bp, exc)

    # ------------------------------------------------------------------ stream

    def stream(self) -> Iterator[Event]:
        offsets: dict[str, int] = {}
        inodes: dict[str, int] = {}

        for p in self.paths:
            try:
                st = os.stat(p)
                offsets[p] = self._load_offset(p) if not self.from_start else 0
                inodes[p] = st.st_ino
            except FileNotFoundError:
                log.info("file_tail.missing path=%s (will retry)", p)
                offsets[p] = 0
                inodes[p] = -1

        while True:
            progressed = False
            for p in self.paths:
                try:
                    st = os.stat(p)
                except FileNotFoundError:
                    continue

                # Rotation detection: inode changed → start from 0.
                if st.st_ino != inodes.get(p):
                    log.info("file_tail.rotated path=%s", p)
                    offsets[p] = 0
                    inodes[p] = st.st_ino

                # Size shrink (truncation) → restart from 0.
                if st.st_size < offsets.get(p, 0):
                    log.info("file_tail.truncated path=%s", p)
                    offsets[p] = 0

                if st.st_size == offsets.get(p, 0):
                    continue

                progressed = True
                try:
                    with open(p, "rb") as f:
                        f.seek(offsets[p])
                        for raw in f:
                            if len(raw) > self.max_line_bytes:
                                log.warning("file_tail.line_too_long path=%s len=%d",
                                            p, len(raw))
                                continue
                            if not raw.strip():
                                continue
                            yield Event(
                                raw_bytes=raw.rstrip(b"\r\n"),
                                source=self.hostname,
                                source_type="file_tail",
                                filename=os.path.basename(p),
                                content_type="text/plain",
                            )
                        new_offset = f.tell()
                    offsets[p] = new_offset
                    self._save_offset(p, new_offset)
                except FileNotFoundError:
                    continue
                except Exception as exc:
                    log.error("file_tail.read_failed path=%s err=%s", p, exc)

            if not progressed:
                time.sleep(self.poll_seconds)

    def read_once(self, limit: int = 100) -> Iterator[Event]:
        count = 0
        for p in self.paths:
            if not Path(p).exists():
                continue
            try:
                size = os.path.getsize(p)
                # Read last up to 64 KB and yield up to `limit` trailing lines.
                read_size = min(size, 65536)
                with open(p, "rb") as f:
                    f.seek(size - read_size)
                    data = f.read()
                for raw in data.splitlines()[-limit:]:
                    if not raw.strip():
                        continue
                    yield Event(
                        raw_bytes=raw,
                        source=self.hostname,
                        source_type="file_tail",
                        filename=os.path.basename(p),
                        content_type="text/plain",
                    )
                    count += 1
                    if count >= limit:
                        return
            except Exception as exc:
                log.error("file_tail.once_failed path=%s err=%s", p, exc)