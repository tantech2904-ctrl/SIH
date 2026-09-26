"""Adapter lifecycle manager.

Owns the threads for currently-running adapters. Provides per-adapter
start/stop so the connector can converge on the backend's desired state.

Thread model:
  - One thread per running adapter, tracked in `_running`.
  - Each adapter has its own `stop_event` — setting it causes the adapter
    worker to stop gracefully between events.
  - `reconcile(desired)` diffs desired vs running and starts/stops as
    needed. Returns a summary so the caller can log what changed.
"""
from __future__ import annotations

import logging
import threading

from ulpf_connector.adapters import available_adapter_names, _all_adapter_classes
from ulpf_connector.adapters.base import BaseAdapter
from ulpf_connector.core.queue import SpoolQueue

log = logging.getLogger(__name__)


class AdapterLifecycleManager:
    def __init__(self, queue: SpoolQueue, *, on_event) -> None:
        """on_event(payload_dict) is called for each event a running
        adapter produces. The caller decides whether to enqueue, count,
        etc.
        """
        self._queue = queue
        self._on_event = on_event
        self._lock = threading.Lock()
        self._running: dict[str, tuple[BaseAdapter, threading.Thread, threading.Event]] = {}

    def available(self) -> list[str]:
        return available_adapter_names()

    def running(self) -> list[str]:
        with self._lock:
            return sorted(self._running.keys())

    def start(self, adapter: BaseAdapter) -> bool:
        with self._lock:
            if adapter.name in self._running:
                log.debug("lifecycle.already_running name=%s", adapter.name)
                return False
            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._run_adapter,
                args=(adapter, stop_event),
                name=f"adapter:{adapter.name}",
                daemon=True,
            )
            self._running[adapter.name] = (adapter, thread, stop_event)
            thread.start()
        log.info("lifecycle.started name=%s", adapter.name)
        return True

    def stop(self, adapter_name: str, *, timeout: float = 5.0) -> bool:
        with self._lock:
            entry = self._running.pop(adapter_name, None)
        if entry is None:
            log.debug("lifecycle.not_running name=%s", adapter_name)
            return False
        _, thread, stop_event = entry
        stop_event.set()
        thread.join(timeout=timeout)
        log.info(
            "lifecycle.stopped name=%s still_alive=%s",
            adapter_name, thread.is_alive(),
        )
        return True

    def stop_all(self, *, timeout: float = 5.0) -> None:
        for name in list(self.running()):
            self.stop(name, timeout=timeout)

    def reconcile(self, desired: list[str] | None) -> dict[str, list[str]]:
        """Converge the running set on `desired`.

        `desired = None` means "no opinion" — no changes.
        `desired = []` means "stop everything" (kill switch).
        Adapter names in `desired` that this host doesn't support are
        reported under "unsupported" and otherwise ignored.
        """
        result: dict[str, list[str]] = {"started": [], "stopped": [], "unsupported": []}
        if desired is None:
            return result

        desired_set = set(desired)
        available_set = set(self.available())
        running_set = set(self.running())

        result["unsupported"] = sorted(desired_set - available_set)
        to_start = sorted((desired_set & available_set) - running_set)
        to_stop = sorted(running_set - desired_set)

        for name in to_stop:
            if self.stop(name):
                result["stopped"].append(name)

        for name in to_start:
            adapter = self._construct(name)
            if adapter and self.start(adapter):
                result["started"].append(name)

        if result["unsupported"]:
            log.warning("lifecycle.unsupported_adapters %s", result["unsupported"])

        return result

    def _construct(self, name: str) -> BaseAdapter | None:
        for cls in _all_adapter_classes():
            if cls.name == name:
                try:
                    return cls({})
                except Exception as exc:
                    log.error("lifecycle.construct_failed name=%s err=%s", name, exc)
                    return None
        log.warning("lifecycle.unknown_adapter name=%s", name)
        return None

    def _run_adapter(self, adapter: BaseAdapter, stop_event: threading.Event) -> None:
        try:
            for event in adapter.stream():
                if stop_event.is_set():
                    log.info("lifecycle.graceful_exit name=%s", adapter.name)
                    return
                self._on_event(event.to_payload())
        except Exception as exc:
            log.exception("adapter.crashed name=%s err=%s", adapter.name, exc)