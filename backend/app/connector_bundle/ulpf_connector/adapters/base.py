"""Adapter interface. Every source adapter implements this contract.

Adapters are pure generators: they read from the OS and yield Events.
They MUST NOT perform HTTP, must NOT write to the backend, and MUST NOT
mutate host state outside of an optional bookmark file (which is theirs
to own and is documented per adapter).

Adapters MUST be resumable: on restart, they should not replay events the
operator already saw. Bookmark files make this possible.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass
class Event:
    """One log event ready for ingestion."""
    raw_bytes: bytes
    source: str
    source_type: str
    filename: str
    content_type: str

    def to_payload(self) -> dict:
        # /api/v1/ingest expects `raw` as a string; UTF-8 is the safe bet
        # across all three OS sources we support.
        return {
            "raw": self.raw_bytes.decode("utf-8", errors="replace"),
            "source": self.source,
            "source_type": self.source_type,
            "filename": self.filename,
            "content_type": self.content_type,
        }


class BaseAdapter(ABC):
    """Base class for source adapters."""

    name: str = "base"

    def __init__(self, config: dict) -> None:
        self.config = config or {}

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this adapter's source is present on this host."""

    @abstractmethod
    def stream(self) -> Iterator[Event]:
        """Yield Events as they arrive.

        Blocks between events. Should exit cleanly on KeyboardInterrupt.
        Should resume from its bookmark (if any) on restart so events are
        not duplicated.
        """

    def read_once(self, limit: int = 100) -> Iterator[Event]:
        """Read whatever is currently available (up to `limit`), then stop.

        Used by --once mode for smoke tests. Default implementation calls
        stream() and stops after `limit` events; adapters may override for
        a more precise "last N" query.
        """
        count = 0
        for ev in self.stream():
            yield ev
            count += 1
            if count >= limit:
                return