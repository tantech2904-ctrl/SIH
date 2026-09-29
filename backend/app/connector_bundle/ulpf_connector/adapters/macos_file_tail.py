"""macOS file-tail adapter.

Reuses the Linux file-tail implementation with macOS-specific defaults.
"""
from __future__ import annotations

import platform
from pathlib import Path

from .linux_file_tail import LinuxFileTailAdapter


DEFAULT_MACOS_PATHS = [
    "/var/log/system.log",
    "/var/log/install.log",
]


class MacOSFileTailAdapter(LinuxFileTailAdapter):
    name = "macos_file_tail"

    def _default_paths(self) -> list[str]:
        return [p for p in DEFAULT_MACOS_PATHS if Path(p).exists()]

    def is_available(self) -> bool:
        return platform.system() == "Darwin" and any(
            Path(p).exists() for p in self.paths
        )