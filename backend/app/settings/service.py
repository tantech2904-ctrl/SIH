"""Settings read/write/hot-reload service."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings, reload_settings
from app.core.logging import get_logger
from app.services.audit_service import record_audit
from app.settings.editable import (
    EDITABLE_KEYS, EDITABLE_KEY_MAP, MASKED_SENTINEL, EditableKey,
)

log = get_logger(__name__)

# The file the UI reads and writes. In Docker this is bind-mounted from
# the host .env; in local dev it may not exist and we fall back to .env.
ENV_LIVE_PATH = Path(os.environ.get("ULPF_ENV_LIVE", "/app/.env.live"))
ENV_FALLBACK_PATH = Path(os.environ.get("ULPF_ENV_FILE", ".env"))


def _active_env_path() -> Path:
    if ENV_LIVE_PATH.exists():
        return ENV_LIVE_PATH
    return ENV_FALLBACK_PATH


def _read_current_values() -> dict[str, str]:
    from app.settings.env_file import read_env_file
    path = _active_env_path()
    values = read_env_file(path) if path.exists() else {}
    # Fill in values from the running Settings object for anything missing
    for k in EDITABLE_KEY_MAP:
        if k not in values:
            v = getattr(settings, k, "")
            values[k] = "" if v is None else str(v)
    return values


def _mask(value: str, sensitive: bool) -> str:
    if not sensitive:
        return value
    return MASKED_SENTINEL if value else ""


def _coerce_and_validate(spec: EditableKey, raw: str) -> str:
    """Convert a raw string from the UI into the canonical string form.
    Raises ValueError with a human message on failure."""
    raw = "" if raw is None else str(raw)
    if spec.type == "bool":
        low = raw.strip().lower()
        if low in ("true", "1", "yes", "on"): return "true"
        if low in ("false", "0", "no", "off", ""): return "false"
        raise ValueError(f"{spec.key} must be true or false, got {raw!r}")
    if spec.type == "int":
        try:
            int(raw)
        except ValueError:
            raise ValueError(f"{spec.key} must be an integer, got {raw!r}")
        return str(int(raw))
    if spec.type == "float":
        try:
            float(raw)
        except ValueError:
            raise ValueError(f"{spec.key} must be a number, got {raw!r}")
        return str(float(raw))
    if spec.type == "csv":
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return ",".join(parts)
    return raw


def get_settings_for_ui() -> dict:
    """Return grouped structure with masked sensitive values."""
    values = _read_current_values()

    groups: dict[str, list[dict]] = {}
    for spec in EDITABLE_KEYS:
        raw = values.get(spec.key, "")
        is_set = bool(raw)
        entry = {
            "key": spec.key,
            "label": spec.label,
            "type": spec.type,
            "sensitive": spec.sensitive,
            "requires_restart": spec.requires_restart,
            "description": spec.description,
            "value": _mask(raw, spec.sensitive),
            "is_set": is_set,
        }
        groups.setdefault(spec.group, []).append(entry)

    ordered = [
        {"name": g, "items": items}
        for g, items in groups.items()
    ]
    return {
        "groups": ordered,
        "env_file": str(_active_env_path()),
        "masked_sentinel": MASKED_SENTINEL,
    }


def update_settings(
    db: Session,
    *,
    actor: str,
    updates: dict[str, str],
) -> dict:
    """Validate, write, audit, hot-reload. Returns a summary dict."""
    from app.settings.env_file import update_env_file

    rejected: list[dict] = []
    accepted: dict[str, str] = {}
    requires_restart: list[str] = []

    for key, raw in updates.items():
        spec = EDITABLE_KEY_MAP.get(key)
        if spec is None:
            rejected.append({"key": key, "reason": "not in allowlist"})
            continue
        # Masked sentinel means "leave unchanged"
        if spec.sensitive and raw == MASKED_SENTINEL:
            continue
        try:
            coerced = _coerce_and_validate(spec, raw)
        except ValueError as e:
            rejected.append({"key": key, "reason": str(e)})
            continue
        accepted[key] = coerced
        if spec.requires_restart:
            requires_restart.append(key)

    if rejected:
        return {
            "updated": [],
            "rejected": rejected,
            "requires_restart": [],
            "restart_required": False,
        }

    if not accepted:
        return {
            "updated": [],
            "rejected": [],
            "requires_restart": [],
            "restart_required": False,
        }

    # Capture previous state for the audit entry
    previous = _read_current_values()
    previous_snapshot = {k: previous.get(k, "") for k in accepted}

    update_env_file(_active_env_path(), accepted)

    # Audit
    audit = record_audit(
        db,
        actor=actor,
        action="SETTINGS_UPDATE",
        resource="settings",
        previous_state={k: _mask(v, EDITABLE_KEY_MAP[k].sensitive) for k, v in previous_snapshot.items()},
        new_state={k: _mask(v, EDITABLE_KEY_MAP[k].sensitive) for k, v in accepted.items()},
    )
    db.commit()

    # Hot-reload
    try:
        reload_settings()
    except Exception as e:
        log.exception("settings.reload_failed", error=str(e))

    return {
        "updated": list(accepted.keys()),
        "rejected": [],
        "requires_restart": requires_restart,
        "restart_required": bool(requires_restart),
        "audit_id": audit.audit_id,
    }