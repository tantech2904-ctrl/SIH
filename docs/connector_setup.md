# Connector Setup

ULPF's connector streams native log sources from the machine you run it on
into the ULPF backend. It is optional — ULPF works without it, and you can
ingest events manually through the UI or the REST API.

This document explains what the connector does, why it needs elevated
privileges the first time, and how to verify it's running.

---

## What the connector reads

| OS      | Source                    | Adapter              |
|---------|---------------------------|----------------------|
| Windows | Event Log channels        | `windows_eventlog`   |
| Linux   | systemd journal           | `linux_journald`     |
| Linux   | Files (auth.log, syslog…) | `linux_file_tail`    |
| macOS   | Unified Log               | `macos_unified_log`  |
| macOS   | Files (system.log…)       | `macos_file_tail`    |

On Windows, the connector watches three channels: **Security**, **System**,
and **Application**.

---

## Why the first run needs Administrator

The Windows Security channel is protected by the operating system. Only
processes running as SYSTEM or with Administrator privileges can read it.
There is no way around this — it is a Windows API security boundary, not a
ULPF design choice.

To handle this cleanly, ULPF installs the connector as a **Windows Scheduled
Task running as SYSTEM**. Once installed:

- The connector starts automatically at boot.
- It has full access to all three channels, including Security.
- No admin window is needed on subsequent runs.
- It restarts automatically if it crashes.

**The UAC prompt you see on first run is a one-time event.** After that,
running `ulpf.bat` is silent.

---

## What `ulpf.bat` does automatically

When you run `ulpf.bat`:

1. Checks for Python 3.10+ on the host.
2. If Python is present:
   - Creates `%USERPROFILE%\.ulpf\connector.json` from the template.
   - Normalizes the config (ensures Security/System/Application are watched).
   - Checks whether the connector service is installed and running.
   - If not installed, prompts for elevation once and installs it.
   - Prints the resulting status.
3. If Python is absent, skips the connector entirely with a clear message.

You do not need to do anything manually unless you want to uninstall the
connector or debug an issue.

---

## Verifying the connector is running

**From the ULPF UI:**

Open the **Connectors** page. You should see your hostname with a green
"Online" badge. Under **Last Heartbeat**, a timestamp within the last
minute. Under **Adapters**, `windows_eventlog`.

**From a PowerShell window:**

```powershell
schtasks /Query /TN "ULPF\Connector" /FO LIST /V