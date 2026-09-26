# ULPF Connector — Cross-Platform Real-Time Log Ingestion

Streams native log sources from Windows, Linux, and macOS hosts into a ULPF
backend's `/api/v1/ingest` endpoint in real time.

One connector, one config file, three OSes. No backend changes required —
the connector is a pure client of the existing ingest API.

---

## What it reads

| OS      | Source                    | Adapter              | Native mechanism                                |
|---------|---------------------------|----------------------|-------------------------------------------------|
| Windows | Event Log channels        | `windows_eventlog`   | `pywin32` (preferred) / `wevtutil` (fallback)   |
| Linux   | systemd journal           | `linux_journald`     | `systemd.journal` (preferred) / `journalctl`    |
| Linux   | Files (auth.log, syslog…) | `linux_file_tail`    | Native Python tailer with rotation handling     |
| macOS   | Unified Log               | `macos_unified_log`  | `log stream --style=json`                       |
| macOS   | Files (system.log…)       | `macos_file_tail`    | Native Python tailer with rotation handling     |

Adapters auto-detect availability. In a fresh config, `"enabled": "auto"`
lets each adapter decide based on the host OS and available dependencies.

---

## Quick start

1. Install dependencies:

   ```bash
   pip install -r requirements.txt

---

## Bookmark and startup policy

Each adapter that reads from a historical source (Windows Event Log,
systemd journal) keeps a bookmark of the last record it delivered to the
backend. The startup behavior is controlled by `resume_from_bookmark`:

- **`false` (default)** — On startup, anchor to the current tail of the
  source. Only events that occur *after* the connector starts are streamed.
  Demo-friendly: no historical flood, no surprise backlog.

- **`true`** — On startup, catch up from the last bookmark. Every event
  that occurred while the connector was down is delivered. Production-friendly:
  nothing is lost across downtime.

To override for a single run without editing config:

```powershell
python connector.py --skip-history