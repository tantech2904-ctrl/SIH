"""Heartbeat + config-poll thread.

Heartbeat: every 60s, tells the backend who we are, what adapters we
*could* run, and which are currently running.

Config poll: every N seconds (N from the backend, default 30s), fetches
`desired_adapters` and reconciles the running set.
"""
from __future__ import annotations

import logging
import platform
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx

log = logging.getLogger(__name__)


def load_or_create_connector_id() -> str:
    path = Path("~/.ulpf/connector_id").expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text().strip()
    cid = str(uuid.uuid4())
    path.write_text(cid)
    return cid


class EventsCounter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total = 0
        self.last_event_at: datetime | None = None

    def incr(self) -> None:
        with self._lock:
            self.total += 1
            self.last_event_at = datetime.now(timezone.utc)

    def last_event_at_iso(self) -> str | None:
        with self._lock:
            if self.last_event_at is None:
                return None
            return self.last_event_at.isoformat()


class HeartbeatThread(threading.Thread):
    def __init__(
        self,
        *,
        base_url: str,
        auth_header: Callable[[], dict | None],
        reauth_fn: Callable[[], bool] | None = None,
        running_adapters_fn: Callable[[], list[str]],
        available_adapters: list[str],
        events_counter: EventsCounter,
        interval_s: float = 60.0,
        version: str = "1.0.0",
    ) -> None:
        super().__init__(name="heartbeat", daemon=True)
        self.base_url = base_url.rstrip("/")
        self.auth_header = auth_header
        self.reauth_fn = reauth_fn
        self.running_adapters_fn = running_adapters_fn
        self.available_adapters = available_adapters
        self.counter = events_counter
        self.interval_s = interval_s
        self.version = version
        self.connector_id = load_or_create_connector_id()
        self._stop = threading.Event()
        self._client = httpx.Client(timeout=10.0)

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self.send_once()
            except Exception as exc:
                log.warning("heartbeat.failed err=%s", exc)
            self._stop.wait(self.interval_s)

    def send_once(self) -> None:
        hdrs = self.auth_header() or {}
        payload = {
            "connector_id": self.connector_id,
            "hostname": platform.node() or "unknown",
            "os": platform.system(),
            "version": self.version,
            "adapters": self.running_adapters_fn(),
            "available_adapters": self.available_adapters,
            "events_total": self.counter.total,
            "last_event_at": self.counter.last_event_at_iso(),
        }
        r = self._client.post(
            f"{self.base_url}/api/v1/connectors/heartbeat",
            json=payload,
            headers=hdrs,
        )
        if r.status_code == 401 and self.reauth_fn:
            log.info("heartbeat.401 re-authenticating")
            if self.reauth_fn():
                hdrs = self.auth_header() or {}
                r = self._client.post(
                    f"{self.base_url}/api/v1/connectors/heartbeat",
                    json=payload,
                    headers=hdrs,
                )
        if r.status_code == 200:
            log.debug("heartbeat.ok")
        else:
            log.warning("heartbeat.http status=%s body=%s", r.status_code, r.text[:200])

    def fetch_config(self) -> dict | None:
        hdrs = self.auth_header() or {}
        try:
            r = self._client.get(
                f"{self.base_url}/api/v1/connectors/{self.connector_id}/config",
                headers=hdrs,
            )
            if r.status_code == 401 and self.reauth_fn:
                log.info("config_poll.401 re-authenticating")
                if self.reauth_fn():
                    hdrs = self.auth_header() or {}
                    r = self._client.get(
                        f"{self.base_url}/api/v1/connectors/{self.connector_id}/config",
                        headers=hdrs,
                    )
            if r.status_code == 200:
                return r.json()
            log.warning("config_poll.http status=%s", r.status_code)
        except Exception as exc:
            log.warning("config_poll.fetch_failed err=%s", exc)
        return None


class ConfigPollerThread(threading.Thread):
    """Polls the backend for desired adapter state and reconciles via the
    AdapterLifecycleManager."""

    def __init__(
        self,
        *,
        heartbeat: HeartbeatThread,
        lifecycle,
        default_interval_s: float = 30.0,
    ) -> None:
        super().__init__(name="config-poller", daemon=True)
        self.heartbeat = heartbeat
        self.lifecycle = lifecycle
        self.interval_s = default_interval_s
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        # Give the first heartbeat time to register the connector on the backend.
        self._stop.wait(5.0)
        while not self._stop.is_set():
            try:
                cfg = self.heartbeat.fetch_config()
                if cfg is not None:
                    desired = cfg.get("desired_adapters")
                    pi = cfg.get("poll_interval_s")
                    if isinstance(pi, (int, float)) and pi >= 5:
                        self.interval_s = float(pi)
                    result = self.lifecycle.reconcile(desired)
                    if result["started"] or result["stopped"] or result["unsupported"]:
                        log.info("config_poll.reconciled %s", result)
            except Exception as exc:
                log.warning("config_poll.error err=%s", exc)
            self._stop.wait(self.interval_s)