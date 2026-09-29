"""Adapter registry.

Auto-detects which adapters are available on this host. Each adapter
reports availability via is_available(); the connector only enables the
ones that pass (or are explicitly forced in config).
"""
from __future__ import annotations

import logging
import platform
from typing import Type

from .base import BaseAdapter, Event

log = logging.getLogger(__name__)

def available_adapter_names() -> list[str]:
    """Names of every adapter this host *could* run, based on OS.

    This does not call is_available() on each adapter — some adapters
    may exist on this OS but be temporarily unavailable (file missing,
    missing optional dependency). This is the *capability* list the
    connector reports to the backend so the UI knows what toggles to
    show.
    """
    return [cls.name for cls in _all_adapter_classes()]

def _all_adapter_classes() -> list[Type[BaseAdapter]]:
    """Import lazily so a missing optional dependency on one platform
    doesn't break adapter discovery on another."""
    classes: list[Type[BaseAdapter]] = []
    system = platform.system()

    try:
        if system == "Windows":
            from .windows_eventlog import WindowsEventLogAdapter
            classes.append(WindowsEventLogAdapter)
        elif system == "Linux":
            from .linux_journald import LinuxJournaldAdapter
            from .linux_file_tail import LinuxFileTailAdapter
            classes.append(LinuxJournaldAdapter)
            classes.append(LinuxFileTailAdapter)
        elif system == "Darwin":
            from .macos_unified_log import MacOSUnifiedLogAdapter
            from .macos_file_tail import MacOSFileTailAdapter
            classes.append(MacOSUnifiedLogAdapter)
            classes.append(MacOSFileTailAdapter)
    except Exception as exc:
        log.error("adapter.import_failed system=%s err=%s", system, exc)

    return classes


def build_adapters(adapter_config: dict) -> list[BaseAdapter]:
    """Instantiate enabled adapters. adapter_config maps adapter name → dict."""
    out: list[BaseAdapter] = []
    for cls in _all_adapter_classes():
        cfg = adapter_config.get(cls.name) or {}
        enabled = cfg.get("enabled", "auto")
        try:
            adapter = cls(cfg)
        except Exception as exc:
            log.error("adapter.construct_failed name=%s err=%s", cls.name, exc)
            continue

        if enabled is False:
            log.info("adapter.disabled_by_config name=%s", cls.name)
            continue
        if enabled is True:
            log.info("adapter.enabled_by_config name=%s", cls.name)
            out.append(adapter)
            continue
        # "auto"
        try:
            avail = adapter.is_available()
        except Exception as exc:
            log.warning("adapter.availability_check_failed name=%s err=%s", cls.name, exc)
            avail = False
        if avail:
            log.info("adapter.auto_enabled name=%s", cls.name)
            out.append(adapter)
        else:
            log.info("adapter.auto_skipped name=%s", cls.name)

    return out


__all__ = ["BaseAdapter", "Event", "build_adapters", "available_adapter_names"]