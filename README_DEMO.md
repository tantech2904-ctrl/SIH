# ULPF SIEM — SIH 2024 Demo Guide

**Universal Log Pre-Processing Framework** — A full-stack Security Information and Event Management (SIEM) platform built for Smart India Hackathon 2024.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Docker Desktop** | [Download here](https://www.docker.com/products/docker-desktop/) — the only install needed |
| **RAM** | 4 GB free |
| **Disk** | 5 GB free (for images + runtime data) |
| **OS** | Windows 10/11 with WSL2 enabled |

**No internet connection required** after images are loaded. Works fully offline / air-gapped.

---

## Quick Start

1. Double-click **`scripts\import_and_run.bat`**
2. First run loads Docker images (~5 minutes). Browser opens automatically.
3. Log in as **Admin** — all features unlocked.

---

## Demo Credentials

| Role | Email | Password | Notes |
|---|---|---|---|
| ⭐ **Admin** | `admin@ulpf.local` | `ChangeMe_Admin123!` | **Recommended for judges** — full access |
| **Analyst** | `analyst@ulpf.local` | `ChangeMe_Analyst123!` | Ingest, analyze, and respond |
| **Auditor** | `auditor@ulpf.local` | `ChangeMe_Auditor123!` | Read-only audit & compliance |

> **Start as Admin** to see all platform features including Settings, Test Lab, and User Management.

---

## 2-Minute Demo Flow

| Step | Action | What you see |
|---|---|---|
| 1 | Log in as Admin | Dashboard with live clock and KPI cards |
| 2 | Click **[Site Tour]** in the top bar | Guided walkthrough of all 11 core features including ML Dataset Export |
| 3 | Click **[▶ Run Demo]** on Dashboard | 11 attack scenarios fire over 12 seconds while KPI counters update live |
| 4 | Toast alert appears → click it | Navigates to Alerts page with populated incidents |
| 5 | Navigate to **Live Stream** | See events streaming in real time via SSE |
| 6 | Open **Event Explorer** | Canonical query + [Export ML Dataset] in JSONL/CSV/JSON + SHA-256 integrity |
| 7 | Visit **Detection → MITRE ATT&CK** | Visual tactic heatmap from ingested events |

---

## Platform Architecture

```
Host Machine (Windows)
├── Docker Desktop
│   ├── ulpf-frontend  → nginx serving React SPA   → http://localhost:5173
│   ├── ulpf-backend   → FastAPI + Celery           → http://localhost:8000
│   ├── ulpf-worker    → Celery background worker
│   ├── ulpf-postgres  → PostgreSQL 16
│   ├── ulpf-redis     → Redis 7
│   └── ulpf-minio     → MinIO object store (evidence)
└── Optional: run_connector.bat (host-side Windows Event Log agent)
```

---

## Live Connector (Optional)

The Windows Event Log Connector streams real host logs (Security, System, Application channels) to the platform. It **cannot run inside Docker** — it needs direct Windows API access.

To enable it:
1. Open `scripts\ulpf-connector\`
2. Right-click `run_connector.bat` → **Run as Administrator**
3. Events appear in Live Stream within seconds

> This is explained with a banner on the Live Stream page.

---

## API Keys — None Required

All external enrichment services are **disabled by default**:

| Service | Status | Notes |
|---|---|---|
| VirusTotal | Disabled | Enable in Settings if key available |
| AbuseIPDB | Disabled | Enable in Settings if key available |
| OTX (AlienVault) | Disabled | Optional |
| MaxMind GeoIP | Disabled | Optional |
| RDAP / DNS | Enabled | Works offline via system resolver |

The platform is **fully functional without any API keys**.

---

## Stopping the Demo

Press **Q** in the terminal window, or run from the project root:
```powershell
docker compose down
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Docker not found | Install Docker Desktop and ensure WSL2 is enabled |
| Port already in use | `docker compose down` then retry; or check with `netstat -ano \| findstr 5173` |
| Dashboard is empty | Click **▶ Run Demo** to populate with synthetic data |
| Slow first start | Normal — Postgres runs migrations on first boot (~45-60s) |
| Images won't load | Ensure `ulpf-sih-demo-images.tar` is next to the script |
