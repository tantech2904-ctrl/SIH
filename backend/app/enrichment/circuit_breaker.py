"""In-memory circuit breaker for external providers."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class _State:
    failures: int = 0
    opened_at: float = 0.0
    open: bool = False


class CircuitBreaker:
    def __init__(self, name: str) -> None:
        self.name = name
        self._state = _State()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if not self._state.open:
                return True
            elapsed = time.time() - self._state.opened_at
            if elapsed >= settings.ENRICHMENT_CIRCUIT_BREAKER_RESET_SECONDS:
                self._state.open = False
                self._state.failures = 0
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._state.failures = 0
            self._state.open = False

    def record_failure(self) -> None:
        with self._lock:
            self._state.failures += 1
            if self._state.failures >= settings.ENRICHMENT_CIRCUIT_BREAKER_FAILURES:
                self._state.open = True
                self._state.opened_at = time.time()


_breakers: dict[str, CircuitBreaker] = {}
_breakers_lock = threading.Lock()


def get_breaker(name: str) -> CircuitBreaker:
    with _breakers_lock:
        if name not in _breakers:
            _breakers[name] = CircuitBreaker(name)
        return _breakers[name]