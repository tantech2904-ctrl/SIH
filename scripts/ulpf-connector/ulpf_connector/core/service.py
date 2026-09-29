"""Service installer for the connector.

Generates and installs a per-OS service unit:
  - Linux:   systemd unit at /etc/systemd/system/ulpf-connector.service
  - macOS:   launchd plist at /Library/LaunchDaemons (--system) or
             ~/Library/LaunchAgents (default user-level)
  - Windows: Scheduled Task "ULPF\\Connector" via schtasks

Contract:
  - install()   is idempotent. Returns 0 if installed-and-running.
                Returns 2 if elevation is required.
  - uninstall() is idempotent. Returns 0 even if nothing was installed.
  - query_status() returns one of:
        "installed,running" | "installed,stopped" | "not_installed"
        | "needs_elevation" | "unsupported"
    and is safe to call un-elevated (it may return "needs_elevation"
    on Windows if querying requires admin).
"""
from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)


SERVICE_NAME = "ulpf-connector"
LAUNCHD_LABEL = "com.ulpf.connector"
WINDOWS_TASK = "ULPF\\Connector"


def _python_executable() -> str:
    return sys.executable


def _connector_script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "connector.py"


def _is_root() -> bool:
    if platform.system() == "Windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return os.geteuid() == 0


# ------------------------------------------------------------------ install

def install(config_path: str, system: bool = False) -> int:
    system_name = platform.system()
    log.info("install.start os=%s system=%s", system_name, system)

    if system_name == "Linux":
        return _install_systemd(config_path)
    if system_name == "Darwin":
        return _install_launchd(config_path, system=system)
    if system_name == "Windows":
        return _install_schtasks(config_path)
    log.error("install.unsupported_os os=%s", system_name)
    return 1


def uninstall(system: bool = False) -> int:
    system_name = platform.system()
    if system_name == "Linux":
        return _uninstall_systemd()
    if system_name == "Darwin":
        return _uninstall_launchd(system=system)
    if system_name == "Windows":
        return _uninstall_schtasks()
    return 1


def query_status(system: bool = False) -> str:
    """Return 'installed,running' | 'installed,stopped' | 'not_installed'
    | 'needs_elevation' | 'unsupported'."""
    system_name = platform.system()
    if system_name == "Linux":
        return _status_systemd()
    if system_name == "Darwin":
        return _status_launchd(system=system)
    if system_name == "Windows":
        return _status_schtasks()
    return "unsupported"


def dry_run(config_path: str, system: bool = False) -> None:
    system_name = platform.system()
    print(f"# Would install on {system_name}")
    print(f"# Config: {config_path}")
    if system_name == "Linux":
        print(f"# Write: /etc/systemd/system/{SERVICE_NAME}.service")
        print(f"# Run:   systemctl daemon-reload")
        print(f"# Run:   systemctl enable --now {SERVICE_NAME}.service")
    elif system_name == "Darwin":
        target = "Library/LaunchDaemons" if system else "Library/LaunchAgents"
        print(f"# Write: {Path.home() if not system else '/'}/{target}/{LAUNCHD_LABEL}.plist")
        print(f"# Run:   launchctl load -w <plist>")
    elif system_name == "Windows":
        print(f"# Run: schtasks /Create /TN \"{WINDOWS_TASK}\" /SC ONSTART /RU SYSTEM "
              f"/RL HIGHEST /TR \"{_python_executable()} {_connector_script_path()} --config {config_path}\"")
        print(f"# Run: schtasks /Run /TN \"{WINDOWS_TASK}\"")


# ------------------------------------------------------------------ systemd

def _systemd_unit_path() -> Path:
    return Path(f"/etc/systemd/system/{SERVICE_NAME}.service")


def _systemd_unit_text(config_path: str) -> str:
    return f"""[Unit]
Description=ULPF Connector — cross-platform log ingestion
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={_python_executable()} {_connector_script_path()} --config {config_path}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""


def _install_systemd(config_path: str) -> int:
    if not _is_root():
        print("ERROR: systemd install requires root. Re-run with sudo.", file=sys.stderr)
        return 2
    if not shutil.which("systemctl"):
        print("ERROR: systemctl not found — this host is not running systemd.", file=sys.stderr)
        return 1

    unit_path = _systemd_unit_path()
    wrote = False
    try:
        unit_path.write_text(_systemd_unit_text(config_path))
        wrote = True
        for cmd in (
            ["systemctl", "daemon-reload"],
            ["systemctl", "enable", f"{SERVICE_NAME}.service"],
            ["systemctl", "restart", f"{SERVICE_NAME}.service"],
        ):
            rc = subprocess.call(cmd)
            if rc != 0:
                raise RuntimeError(f"command failed: {' '.join(cmd)}")
        rc = subprocess.call(["systemctl", "is-active", f"{SERVICE_NAME}.service"])
        if rc != 0:
            raise RuntimeError("service is not active after start")
        print(f"OK: {SERVICE_NAME} installed and running.")
        return 0
    except Exception as exc:
        log.error("install.systemd_failed err=%s", exc)
        if wrote:
            try:
                unit_path.unlink()
                subprocess.call(["systemctl", "daemon-reload"])
            except Exception:
                pass
        print(f"ERROR: install failed: {exc}", file=sys.stderr)
        return 1


def _uninstall_systemd() -> int:
    if not _is_root():
        print("ERROR: systemd uninstall requires root. Re-run with sudo.", file=sys.stderr)
        return 2
    subprocess.call(["systemctl", "stop", f"{SERVICE_NAME}.service"])
    subprocess.call(["systemctl", "disable", f"{SERVICE_NAME}.service"])
    unit_path = _systemd_unit_path()
    if unit_path.exists():
        unit_path.unlink()
    subprocess.call(["systemctl", "daemon-reload"])
    print(f"OK: {SERVICE_NAME} uninstalled.")
    return 0


def _status_systemd() -> str:
    if not _systemd_unit_path().exists():
        return "not_installed"
    rc = subprocess.call(
        ["systemctl", "is-active", "--quiet", f"{SERVICE_NAME}.service"]
    )
    return "installed,running" if rc == 0 else "installed,stopped"


# ------------------------------------------------------------------ launchd

def _launchd_plist_path(system: bool) -> Path:
    target_dir = Path("/Library/LaunchDaemons") if system else (Path.home() / "Library/LaunchAgents")
    return target_dir / f"{LAUNCHD_LABEL}.plist"


def _launchd_plist_text(config_path: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LAUNCHD_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{_python_executable()}</string>
    <string>{_connector_script_path()}</string>
    <string>--config</string>
    <string>{config_path}</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/{LAUNCHD_LABEL}.out.log</string>
  <key>StandardErrorPath</key><string>/tmp/{LAUNCHD_LABEL}.err.log</string>
</dict>
</plist>
"""


def _install_launchd(config_path: str, system: bool) -> int:
    if system and not _is_root():
        print("ERROR: system-level launchd install requires root. Re-run with sudo.", file=sys.stderr)
        return 2
    plist = _launchd_plist_path(system)
    plist.parent.mkdir(parents=True, exist_ok=True)

    try:
        if plist.exists():
            subprocess.call(["launchctl", "unload", "-w", str(plist)])
        plist.write_text(_launchd_plist_text(config_path))
        rc = subprocess.call(["launchctl", "load", "-w", str(plist)])
        if rc != 0:
            raise RuntimeError(f"launchctl load failed rc={rc}")
        print(f"OK: {LAUNCHD_LABEL} installed and loaded.")
        return 0
    except Exception as exc:
        log.error("install.launchd_failed err=%s", exc)
        try:
            if plist.exists():
                plist.unlink()
        except Exception:
            pass
        print(f"ERROR: install failed: {exc}", file=sys.stderr)
        return 1


def _uninstall_launchd(system: bool) -> int:
    plist = _launchd_plist_path(system)
    subprocess.call(["launchctl", "unload", "-w", str(plist)])
    if plist.exists():
        plist.unlink()
    print(f"OK: {LAUNCHD_LABEL} uninstalled.")
    return 0


def _status_launchd(system: bool) -> str:
    plist = _launchd_plist_path(system)
    if not plist.exists():
        return "not_installed"
    rc = subprocess.call(["launchctl", "list", LAUNCHD_LABEL])
    return "installed,running" if rc == 0 else "installed,stopped"


# ------------------------------------------------------------------ schtasks

def _install_schtasks(config_path: str) -> int:
    if not _is_root():
        print("ERROR: Windows install requires elevation (Administrator).", file=sys.stderr)
        return 2

    py_exe = _python_executable()
    script = str(_connector_script_path())

    # Check if python is located in a per-user directory (e.g. AppData\Local\Programs)
    is_user_profile = "\\users\\" in py_exe.lower() or "\\appdata\\" in py_exe.lower()
    user_arg = os.environ.get("USERNAME") if is_user_profile else "SYSTEM"

    # /F overwrites an existing task — idempotent.
    tr_command = f'"{py_exe}" "{script}" --config "{config_path}"'
    cmd = [
        "schtasks", "/Create",
        "/TN", WINDOWS_TASK,
        "/SC", "ONSTART",
        "/RU", user_arg or "SYSTEM",
        "/RL", "HIGHEST",
        "/F",
        "/TR", tr_command,
    ]
    rc = subprocess.call(cmd)
    if rc != 0:
        # Fallback without explicit user or highest privilege if rejected
        cmd_fallback = [
            "schtasks", "/Create",
            "/TN", WINDOWS_TASK,
            "/SC", "ONSTART",
            "/F",
            "/TR", tr_command,
        ]
        rc = subprocess.call(cmd_fallback)
        if rc != 0:
            print(f"ERROR: schtasks /Create failed rc={rc}", file=sys.stderr)
            return 1

    # Start it now so the user doesn't need to reboot.
    rc = subprocess.call(["schtasks", "/Run", "/TN", WINDOWS_TASK])
    if rc != 0:
        print(f"WARN: schtasks /Run failed rc={rc}", file=sys.stderr)
    print(f"OK: scheduled task '{WINDOWS_TASK}' installed.")
    return 0


def _uninstall_schtasks() -> int:
    subprocess.call(["schtasks", "/End", "/TN", WINDOWS_TASK])
    rc = subprocess.call(["schtasks", "/Delete", "/TN", WINDOWS_TASK, "/F"])
    if rc != 0:
        print(f"WARN: schtasks /Delete rc={rc}", file=sys.stderr)
    print(f"OK: scheduled task '{WINDOWS_TASK}' removed.")
    return 0


def _status_schtasks() -> str:
    # Querying the task itself doesn't need elevation; the task simply
    # exists or doesn't.
    try:
        out = subprocess.run(
            ["schtasks", "/Query", "/TN", WINDOWS_TASK, "/FO", "LIST", "/V"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return "not_installed"
    if out.returncode != 0:
        return "not_installed"
    # Look for "Status:        Running" in the verbose listing.
    for line in out.stdout.splitlines():
        s = line.strip()
        if s.lower().startswith("status:"):
            value = s.split(":", 1)[1].strip().lower()
            if "running" in value:
                return "installed,running"
            if "ready" in value or "disabled" in value:
                return "installed,stopped"
    return "installed,stopped"