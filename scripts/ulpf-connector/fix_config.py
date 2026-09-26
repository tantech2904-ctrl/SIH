#!/usr/bin/env python3
"""Fix / normalize ~/.ulpf/connector.json.

Purpose:
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
import sys
from pathlib import Path


REQUIRED_CHANNELS = ["Security", "System", "Application"]
DEFAULT_BOOKMARK = "~/.ulpf/win_eventlog.bookmark.json"


def fix(path: Path, dry_run: bool = False) -> int:
    if not path.exists():
        print(f"[--] {path} does not exist. Nothing to fix.")
        return 0

    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[!!] {path} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    changes: list[str] = []

    adapters = cfg.setdefault("adapters", {})
    win = adapters.setdefault("windows_eventlog", {})

    # 1. channels — ensure all three are present, preserving order.
    current = win.get("channels") or []
    if not isinstance(current, list):
        current = []
    merged = list(dict.fromkeys(
        REQUIRED_CHANNELS + [c for c in current if c not in REQUIRED_CHANNELS]
    ))
    if merged != current:
        changes.append(f"channels: {current} -> {merged}")
        win["channels"] = merged

    # 2. resume_from_bookmark — default false.
    if "resume_from_bookmark" not in win:
        changes.append("resume_from_bookmark: <missing> -> false")
        win["resume_from_bookmark"] = False

    # 3. bookmark_file — default path.
    if not win.get("bookmark_file"):
        changes.append(f"bookmark_file: <missing> -> {DEFAULT_BOOKMARK}")
        win["bookmark_file"] = DEFAULT_BOOKMARK

    # 4. Sanity defaults that the adapter expects but old configs may lack.
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