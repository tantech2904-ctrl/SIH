"""HTTP client for ULPF ingestion.

Responsibilities:
  - Login and cache the bearer token.
  - POST events to /api/v1/ingest with proper backoff on transient failures.
  - Re-authenticate transparently on 401.
  - Respect rate limits (429 → exponential backoff with jitter).
  - Never raise from send() — returns a boolean and logs the outcome.

The contract with the backend is pinned by
backend/tests/test_connector_contracts.py.
"""
from __future__ import annotations

import logging
import random
import threading
import time

import httpx

from .config import ConnectorConfig

log = logging.getLogger(__name__)


class UlpfClient:
    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self._lock = threading.Lock()
        self._token: str | None = None
        self._client = httpx.Client(timeout=config.http.timeout_s)

    # ------------------------------------------------------------------ auth

    def _login(self) -> bool:
        url = f"{self.config.ulpf_base}/api/v1/auth/login"
        try:
            r = self._client.post(
                url,
                json={
                    "email": self.config.auth.email,
                    "password": self.config.resolve_password(),
                },
            )
            if r.status_code != 200:
                log.error("login.failed status=%s body=%s", r.status_code, r.text[:200])
                return False
            token = r.json().get("access_token")
            if not token:
                log.error("login.no_token body=%s", r.text[:200])
                return False
            with self._lock:
                self._token = token
            log.info("login.ok email=%s", self.config.auth.email)
            return True
        except Exception as exc:
            log.error("login.exception err=%s", exc)
            return False

    def _auth_header(self) -> dict[str, str] | None:
        with self._lock:
            tok = self._token
        if tok is None:
            return None
        return {"Authorization": f"Bearer {tok}"}

    def ensure_authenticated(self) -> bool:
        if self._auth_header() is None:
            return self._login()
        return True

    # ------------------------------------------------------------------ send

    def send(self, payload: dict) -> bool:
        """Send one ingest payload. Returns True on success. Never raises."""
        if not self.ensure_authenticated():
            return False

        url = f"{self.config.ulpf_base}/api/v1/ingest"
        attempt = 0
        max_attempts = self.config.http.max_retries

        while attempt <= max_attempts:
            headers = self._auth_header() or {}
            try:
                r = self._client.post(url, json=payload, headers=headers)
            except httpx.RequestError as exc:
                log.warning("send.network_error attempt=%d err=%s", attempt, exc)
                self._backoff(attempt)
                attempt += 1
                continue

            if r.status_code == 200:
                return True

            if r.status_code == 401:
                log.warning("send.401 re-authenticating")
                with self._lock:
                    self._token = None
                if not self._login():
                    self._backoff(attempt)
                    attempt += 1
                    continue
                attempt += 1
                continue

            if r.status_code == 429:
                log.warning("send.429 rate limited, backing off")
                self._backoff(attempt, base=2.0)
                attempt += 1
                continue

            if 500 <= r.status_code < 600:
                log.warning("send.%d server_error attempt=%d body=%s",
                            r.status_code, attempt, r.text[:200])
                self._backoff(attempt)
                attempt += 1
                continue

            # 4xx other than auth/rate-limit → permanent, don't retry.
            log.error("send.permanent_failure status=%s body=%s",
                      r.status_code, r.text[:300])
            return False

        log.error("send.gave_up attempts=%d", attempt)
        return False

    def _backoff(self, attempt: int, base: float | None = None) -> None:
        b = base if base is not None else self.config.http.backoff_base_s
        delay = min(b * (2 ** attempt) + random.uniform(0, b), self.config.http.backoff_max_s)
        time.sleep(delay)

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass