#!/usr/bin/env python3
"""Install, uninstall, or query the connector service.

Linux:   systemd unit at /etc/systemd/system/ulpf-connector.service
macOS:   launchd plist (user-level by default; --system for /Library/LaunchDaemons)
Windows: Scheduled Task "ULPF\\Connector"

Exit codes:
    0  success / already installed and running
    1  generic failure
    2  needs elevation (caller should re-run as Administrator/root)
    3  config file missing

Modes:
    (default)     install + enable + start; idempotent
    --uninstall   stop + remove; idempotent
    --status      print one line `connector.service.status=<state>` and exit
    --dry-run     print planned actions, change nothing

Machine-readable status output:
    connector.service.status=installed,running
    connector.service.status=installed,stopped
    connector.service.status=not_installed
    connector.service.status=needs_elevation
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ulpf_connector.core.logging import setup_logging
from ulpf_connector.core import service as svc


def _emit_status(state: str) -> None:
    print(f"connector.service.status={state}")


def main() -> int:
    ap = argparse.ArgumentParser(description="ULPF connector service installer")
    ap.add_argument("--config", default=str(Path.home() / ".ulpf" / "connector.json"),
                    help="Path to config file the service will use")
    ap.add_argument("--system", action="store_true",
                    help="Install system-wide (macOS launchd). Ignored on Linux/Windows.")
    ap.add_argument("--uninstall", action="store_true", help="Remove the service")
    ap.add_argument("--status", action="store_true",
                    help="Print service status and exit. No changes.")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    setup_logging(args.log_level)

    if args.status:
        state = svc.query_status(system=args.system)
        _emit_status(state)
        if state == "needs_elevation":
            return 2
        return 0

    if args.dry_run:
        svc.dry_run(args.config, system=args.system)
        return 0

    if args.uninstall:
        rc = svc.uninstall(system=args.system)
        return rc

    config_path = Path(args.config).expanduser()
    if not config_path.exists():
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        return 3

    rc = svc.install(str(config_path), system=args.system)
    if rc == 2:
        _emit_status("needs_elevation")
        return 2
    if rc != 0:
        return rc

    state = svc.query_status(system=args.system)
    _emit_status(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())