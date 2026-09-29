"""Editable settings subsystem.

Exposes a strict allowlist of env-var keys that can be read and written
from the UI, plus a line-based .env file rewriter that preserves comments
and non-editable keys.

Public entry points:
  - editable.EDITABLE_KEYS           the allowlist
  - service.get_settings_for_ui()    read current values (masked)
  - service.update_settings()        validate and write updates
  - service.reload_settings()        hot-reload the running Settings object
"""