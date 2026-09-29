"""Logging setup for the connector.

Writes to stdout and (optionally) a rotating file. Uses stdlib logging
only — no third-party dependency. Level configurable via config or CLI.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """Configure the root logger for the connector. Idempotent."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear any pre-existing handlers so repeated calls don't duplicate output.
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    class _FlushingStreamHandler(logging.StreamHandler):
        """StreamHandler that flushes after every emit.

        Without this, log output is buffered when stdout isn't a TTY
        (e.g. when launched from a Scheduled Task or with output piped
        somewhere), and the operator sees nothing until the process
        exits — making hangs impossible to diagnose.
        """
        def emit(self, record):
            super().emit(record)
            try:
                self.flush()
            except Exception:
                pass

    stream = _FlushingStreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    root.addHandler(stream)

    if log_file:
        path = Path(log_file).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        fileh = logging.handlers.RotatingFileHandler(
            path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fileh.setFormatter(fmt)
        root.addHandler(fileh)

    return root