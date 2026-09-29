#!/usr/bin/env python3
"""Fix / normalize connector.json.

Purpose:
  - Ensure `auth.email` and `auth.password` are set with fallback to bootstrap credentials.
  - Ensure the Windows adapter watches Security, System, and Application.
  - Ensure `resume_from_bookmark` is set (default: false — skip history).
  - Ensure `bookmark_file` points at ~/.ulpf/win_eventlog.bookmark.json.
  - Preserve any other keys the user has set (auth, queue, http, other adapters).

Idempotent. Safe to run any number of times. Never removes user data.

Usage:
    python fix_config.py                # fix ~/.ulpf/connector.json
    python fix_config.py --path X       # fix a specific file
    python fix_config.py --dry-run      # print what would change, don't write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REQUIRED_CHANNELS = ["Security", "System", "Application"]
DEFAULT_BOOKMARK = "~/.ulpf/win_eventlog.bookmark.json"
DEFAULT_PASSWORD = "ChangeMe_Admin123!"
DEFAULT_EMAIL = "admin@ulpf.local"


def _find_env_password() -> str | None:
    """Attempt to find admin password from environment or root .env."""
    if os.environ.get("ULPF_CONNECTOR_PASSWORD"):
        return os.environ["ULPF_CONNECTOR_PASSWORD"]
    if os.environ.get("BOOTSTRAP_ADMIN_PASSWORD"):
        return os.environ["BOOTSTRAP_ADMIN_PASSWORD"]

    # Check root .env
    candidates = [
        Path(__file__).resolve().parents[2] / ".env",
        Path.cwd() / ".env",
    ]
    for p in candidates:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("BOOTSTRAP_ADMIN_PASSWORD="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            except Exception:
                pass
    return None


def fix(path: Path, dry_run: bool = False) -> int:
    if not path.exists():
        print(f"[--] {path} does not exist. Creating default normalized config.")
        path.parent.mkdir(parents=True, exist_ok=True)
        default_pwd = _find_env_password() or DEFAULT_PASSWORD
        default_cfg = {
            "ulpf_base": "http://localhost:8000",
            "log_level": "INFO",
            "log_file": str(path.parent / "connector.log"),
            "auth": {
                "email": DEFAULT_EMAIL,
                "password": default_pwd,
                "password_env": "ULPF_CONNECTOR_PASSWORD",
            },
            "queue": {
                "max_in_memory": 1000,
                "spool_file": str(path.parent / "spool.jsonl"),
                "spool_replay_on_start": True,
            },
            "http": {
                "timeout_s": 30.0,
                "max_retries": 5,
                "backoff_base_s": 0.5,
                "backoff_max_s": 30.0,
            },
            "adapters": {
                "windows_eventlog": {
                    "enabled": "auto",
                    "channels": REQUIRED_CHANNELS,
                    "filter_xpath": "*",
                    "poll_seconds": 2.0,
                    "max_events_per_poll": 200,
                    "bookmark_file": str(path.parent / "win_eventlog.bookmark.json"),
                    "resume_from_bookmark": False,
                }
            },
        }
        if not dry_run:
            path.write_text(json.dumps(default_cfg, indent=2) + "\n", encoding="utf-8")
            print(f"[OK] Wrote initial {path}")
        return 0

    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[!!] {path} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    changes: list[str] = []

    # 1. auth - ensure email & password are present and not empty
    auth = cfg.setdefault("auth", {})
    if not auth.get("email"):
        changes.append(f"auth.email: <missing> -> {DEFAULT_EMAIL}")
        auth["email"] = DEFAULT_EMAIL

    if not auth.get("password"):
        resolved_pwd = _find_env_password() or DEFAULT_PASSWORD
        changes.append("auth.password: <empty> -> populated with bootstrap default")
        auth["password"] = resolved_pwd

    auth.setdefault("password_env", "ULPF_CONNECTOR_PASSWORD")

    # 2. adapters - windows_eventlog
    adapters = cfg.setdefault("adapters", {})
    win = adapters.setdefault("windows_eventlog", {})

    current = win.get("channels") or []
    if not isinstance(current, list):
        current = []
    merged = list(dict.fromkeys(
        REQUIRED_CHANNELS + [c for c in current if c not in REQUIRED_CHANNELS]
    ))
    if merged != current:
        changes.append(f"channels: {current} -> {merged}")
        win["channels"] = merged

    if "resume_from_bookmark" not in win:
        changes.append("resume_from_bookmark: <missing> -> false")
        win["resume_from_bookmark"] = False

    if not win.get("bookmark_file"):
        changes.append(f"bookmark_file: <missing> -> {DEFAULT_BOOKMARK}")
        win["bookmark_file"] = DEFAULT_BOOKMARK

    win.setdefault("enabled", "auto")
    win.setdefault("filter_xpath", "*")
    win.setdefault("poll_seconds", 2.0)
    win.setdefault("max_events_per_poll", 200)

    if not changes:
        print(f"[OK] {path} already correct. No changes.")
        return 0

    print(f"[+] {path} — changes:")
    for c in changes:
        print(f"     - {c}")

    if dry_run:
        print("[i] dry-run: file not written.")
        return 0

    backup = path.with_suffix(path.suffix + ".bak")
    try:
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Wrote {path} (backup at {backup.name}).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Fix connector.json")
    ap.add_argument("--path", default=str(Path.home() / ".ulpf" / "connector.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return fix(Path(args.path).expanduser(), dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())