"""Connector configuration loader + validator.

A single JSON file drives every platform. Environment variables override
secrets and a few common knobs so the config file can be committed.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = "~/.ulpf/connector.json"


@dataclass
class AuthConfig:
    email: str = "admin@ulpf.local"
    password: str = ""
    password_env: str = "ULPF_CONNECTOR_PASSWORD"


@dataclass
class QueueConfig:
    max_in_memory: int = 1000
    spool_file: str = "~/.ulpf/spool.jsonl"
    spool_replay_on_start: bool = True


@dataclass
class HttpConfig:
    timeout_s: float = 30.0
    max_retries: int = 5
    backoff_base_s: float = 0.5
    backoff_max_s: float = 30.0


@dataclass
class ConnectorConfig:
    ulpf_base: str = "http://localhost:8000"
    auth: AuthConfig = field(default_factory=AuthConfig)
    queue: QueueConfig = field(default_factory=QueueConfig)
    http: HttpConfig = field(default_factory=HttpConfig)
    adapters: dict[str, dict[str, Any]] = field(default_factory=dict)
    log_level: str = "INFO"
    log_file: str | None = None

    def resolve_password(self) -> str:
        """Resolve the login password from env var if set, else from config."""
        env_val = os.environ.get(self.auth.password_env)
        if env_val:
            return env_val
        return self.auth.password


def load_config(path: str | None = None) -> ConnectorConfig:
    """Load config from disk (or env override). Missing file → defaults."""
    cfg_path = Path(
        path
        or os.environ.get("ULPF_CONNECTOR_CONFIG")
        or DEFAULT_CONFIG_PATH
    ).expanduser()

    raw: dict[str, Any] = {}
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Failed to parse config at {cfg_path}: {exc}") from exc

    # env override for base URL
    base = os.environ.get("ULPF_CONNECTOR_BASE") or raw.get("ulpf_base") or "http://localhost:8000"

    auth_raw = raw.get("auth") or {}
    auth = AuthConfig(
        email=auth_raw.get("email", "admin@ulpf.local"),
        password=auth_raw.get("password", ""),
        password_env=auth_raw.get("password_env", "ULPF_CONNECTOR_PASSWORD"),
    )

    queue_raw = raw.get("queue") or {}
    queue = QueueConfig(
        max_in_memory=int(queue_raw.get("max_in_memory", 1000)),
        spool_file=queue_raw.get("spool_file", "~/.ulpf/spool.jsonl"),
        spool_replay_on_start=bool(queue_raw.get("spool_replay_on_start", True)),
    )

    http_raw = raw.get("http") or {}
    http = HttpConfig(
        timeout_s=float(http_raw.get("timeout_s", 30.0)),
        max_retries=int(http_raw.get("max_retries", 5)),
        backoff_base_s=float(http_raw.get("backoff_base_s", 0.5)),
        backoff_max_s=float(http_raw.get("backoff_max_s", 30.0)),
    )

    return ConnectorConfig(
        ulpf_base=base.rstrip("/"),
        auth=auth,
        queue=queue,
        http=http,
        adapters=raw.get("adapters") or {},
        log_level=raw.get("log_level", "INFO"),
        log_file=raw.get("log_file"),
    )