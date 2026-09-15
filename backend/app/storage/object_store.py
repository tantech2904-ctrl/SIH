"""Abstract object storage interface for raw evidence."""
from __future__ import annotations

from abc import ABC, abstractmethod


class ObjectStore(ABC):
    @abstractmethod
    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Return a storage location descriptor (e.g. bucket/key)."""

    @abstractmethod
    def get_bytes(self, key: str) -> bytes:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def health(self) -> dict:
        ...