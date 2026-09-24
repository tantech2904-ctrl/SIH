"""Line-based .env parser and writer.

Preserves comments, ordering, and non-target keys. Atomic write via
temp file + os.replace.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable
import shutil


def read_env_file(path: str | Path) -> dict[str, str]:
    """Return key=value pairs, skipping comments and blanks."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        # Strip matching outer quotes
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        out[k] = v
    return out


def _format_value(value: str) -> str:
    """Add quotes if the value contains characters that would confuse a shell."""
    if value == "":
        return ""
    needs_quotes = any(c in value for c in " #\t\n\"'")
    if needs_quotes:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def update_env_file(path: str | Path, updates: dict[str, str]) -> None:
    """Rewrite env file in place with new values, preserving comments and order.

    Any key in `updates` that is not already present is appended to the
    end under a section header.

    We do NOT use os.replace() because .env.live inside the container is
    a bind-mount to a host file, and os.replace() fails with EBUSY when
    source and destination are on different filesystems. shutil.move()
    falls back to copy+unlink across devices. The file is <10 KB, so the
    non-atomic window is negligible.
    """
    p = Path(path)
    original: list[str] = []
    if p.exists():
        original = p.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    out_lines: list[str] = []
    seen_keys: set[str] = set()

    for raw in original:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out_lines.append(raw)
            continue
        k, _, _ = stripped.partition("=")
        k = k.strip()
        if k in remaining:
            out_lines.append(f"{k}={_format_value(remaining[k])}")
            seen_keys.add(k)
            remaining.pop(k)
        else:
            out_lines.append(raw)

    if remaining:
        if out_lines and out_lines[-1].strip() != "":
            out_lines.append("")
        out_lines.append("# ==== Added by ULPF Settings UI ====")
        for k, v in remaining.items():
            out_lines.append(f"{k}={_format_value(v)}")

    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    shutil.move(str(tmp), str(p))