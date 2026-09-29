# ULPF SecOps — Unified Log Processing Framework & SIEM
### Developed by Team BEETLES for Smart India Hackathon (SIH)

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Multi--Tenancy](https://img.shields.io/badge/multi--tenant-isolated-success.svg)](https://github.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**ULPF SecOps** is an enterprise-grade, high-throughput Security Information and Event Management (SIEM) and log processing pipeline. It ingests heterogenous security telemetry (Syslog, Windows EVTX, CEF, LEEF, JSON, CSV), normalizes it into a Canonical Security Event (CSE) schema, detects threats via MITRE ATT&CK correlation, and preserves evidence in tamper-evident, SHA-256 hash-chained WORM storage with **full multi-tenant data isolation**.

---

## ⚡ Quick Links & Navigation

1. [Quick Start (One-Click Automated)](#1-quick-start-one-click-automated)
2. [Default Credentials & Demo Personas](#2-default-credentials--demo-personas)
3. [Multi-Tenant Isolated Workspaces](#3-multi-tenant-isolated-workspaces)
4. [Manual Setup Fallback: Docker Compose](#4-manual-setup-fallback-docker-compose)
5. [Manual Setup Fallback: 100% Local Run (No Docker)](#5-manual-setup-fallback-100-local-run-no-docker)
6. [Cloud Hosting (Oracle Cloud / Ubuntu / Debian VPS)](#6-cloud-hosting-oracle-cloud--vps-deployment)
7. [Host Log Connectors (Windows, Linux, macOS)](#7-host-log-connectors-windows-linux-macos)
8. [Platform Architecture & Workspaces](#8-platform-architecture--workspaces)
9. [Troubleshooting & FAQs](#9-troubleshooting--faqs)

---

## 1. Quick Start (One-Click Automated)

The repository provides automated startup scripts with self-healing, environment validation, and container orchestration for all major operating systems:

### 🪟 Windows
Double-click or run in PowerShell / Command Prompt:
```cmd
start_ulpf.bat
```
*(Or use `scripts\setup_ulpf.bat` or `scripts\import_and_run.bat`)*

### 🐧 Linux
Run in your terminal:
```bash
chmod +x start_ulpf.sh
./start_ulpf.sh
```

### 🍎 macOS
Run in your terminal:
```bash
chmod +x start_ulpf_mac.sh
./start_ulpf_mac.sh
```

Once started, the platform will be available at:
- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173) *(or [http://localhost:3000](http://localhost:3000))*
- **Backend REST API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MinIO S3 Evidence Console**: [http://localhost:9001](http://localhost:9001)

---

## 2. Default Credentials & Demo Personas

The login screen provides **1-Click Quick Demo Login** buttons. You can also sign in manually:

| Persona | Email | Password | Role | Description |
|---|---|---|---|---|
| ⭐ **Platform Admin** | `admin@ulpf.local` | `ChangeMe_Admin123!` | `ADMIN` | Unconstrained access across all workspaces, settings, test lab, and users. |
| 🛡️ **Team BEETLES Lead** | `team@ulpf.local` | `ChangeMe_Team123!` | `ADMIN` | Pre-configured **isolated team workspace** demonstrating multi-tenancy. |
| 🔍 **SOC Analyst** | `analyst@ulpf.local` | `ChangeMe_Analyst123!` | `ANALYST` | Real-time log streams, threat alert triage, MITRE ATT&CK exploration. |
| ⚖️ **Compliance Auditor** | `auditor@ulpf.local` | `ChangeMe_Auditor123!` | `AUDITOR` | WORM evidence verification and cryptographic SHA-256 audit ledger. |

---

## 3. Multi-Tenant Isolated Workspaces

ULPF SecOps features **complete data isolation** for teams, judges, and evaluators:

1. **Create or Join a Team Workspace**:
   - On the login screen, click the **"New Workspace"** tab.
   - Enter your Work Email, Password, Full Name, and **Workspace / Team Name** (e.g. `Team BEETLES` or `RedTeam Alpha`).
   - Select your role: **Admin**, **Analyst**, or **Auditor**.
2. **Team Collaboration**:
   - If two or more users enter the same Workspace Name, they **automatically join the same team** and can collaborate, viewing the same live streams, alerts, incidents, and connectors.
   - If a new workspace name is entered, a **cryptographically private tenant sandbox** is created with isolated telemetry, private alerts, private connectors, and isolated WORM object storage.

---

## 4. Manual Setup Fallback: Docker Compose

If the automated `.bat` or `.sh` script encounters an issue on your machine, you can run the entire containerized stack manually using standard Docker Compose:

### Step 1: Ensure Prerequisites
- Docker Engine & Docker Compose (v2.0+) installed and running (`docker --version`).

### Step 2: Initialize Configuration File
Make sure `.env` is a file (not a folder):
```bash
# On Linux / macOS
cp .env.example .env

# On Windows (PowerShell)
Copy-Item .env.example .env
```

### Step 3: Build & Start All Services
```bash
docker compose up -d --build
```

### Step 4: Verify Running Services
```bash
docker compose ps
```
You should see:
- `ulpf-postgres` (PostgreSQL 16) — Port 5432
- `ulpf-redis` (Redis 7) — Port 6379
- `ulpf-openbucket` (MinIO Object Store) — Ports 9000, 9001
- `ulpf-backend` (FastAPI Server) — Port 8000, 5140/udp
- `ulpf-worker` (Celery Processing Engine)
- `ulpf-frontend` (Nginx + React SPA) — Port 5173

### Step 5: View Logs
```bash
# View all logs in real-time
docker compose logs -f

# Or check backend specifically
docker compose logs -f backend
```

### Step 6: Stopping the Containers
```bash
docker compose down
```
*(To stop and purge all database volume state for a fresh start: `docker compose down -v`)*

---

## 5. Manual Setup Fallback: 100% Local Run (No Docker)

If Docker is unavailable, you can run both backend and frontend natively on your host machine.

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: v18.0.0 or higher + `npm`
- **Database**: PostgreSQL 14+ (or set `DATABASE_URL=sqlite:///./ulpf.db` in `.env`)
- **Cache**: Redis (optional; backend handles local fallback)

---

### Step-by-Step Native Execution:

#### 1. Configure the Environment
In the project root:
```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```
*(If using SQLite locally, edit `.env` and set `DATABASE_URL=sqlite:///./ulpf.db`)*

---

#### 2. Start the Backend API
Open **Terminal 1**:

**On Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations and database bootstrap
alembic upgrade head
python -m app.db.init_db

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**On Linux / macOS:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations and database bootstrap
alembic upgrade head
python -m app.db.init_db

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API will be live at: `http://localhost:8000`

---

#### 3. Start the Background Worker (Optional)
Open **Terminal 2** (with virtual environment activated):
```bash
cd backend
# Linux / macOS
source venv/bin/activate
celery -A app.workers.celery_app.celery_app worker --loglevel=info

# Windows
.\venv\Scripts\activate
celery -A app.workers.celery_app.celery_app worker --loglevel=info -P solo
```

---

#### 4. Start the Frontend Application
Open **Terminal 3**:
```bash
cd frontend
npm install
npm run dev
```
The React SPA will launch at: `http://localhost:5173`

---

## 6. Cloud Hosting (Oracle Cloud / VPS Deployment)

To deploy ULPF on an Oracle Cloud Infrastructure (OCI) Free Tier compute instance (Ubuntu / Debian / Oracle Linux):

1. **SSH into your VPS**:
   ```bash
   ssh -i ~/.ssh/id_rsa ubuntu@<YOUR_SERVER_PUBLIC_IP>
   ```

2. **Install Docker & Docker Compose**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y ca-certificates curl gnupg
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   sudo chmod a+r /etc/apt/keyrings/docker.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt-get update
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   sudo usermod -aG docker $USER
   ```
   *(Log out and log back in for docker group to take effect).*

3. **Deploy the Code**:
   ```bash
   git clone <YOUR_REPO_URL> sih-ulpf
   cd sih-ulpf
   cp .env.example .env
   ```

4. **Open Firewall Ports**:
   ```bash
   # Allow Web traffic (Port 5173 or 80) and API (Port 8000)
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5173 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
   sudo netfilter-persistent save 2>/dev/null || true
   ```
   *(Ensure Security List / Ingress Rules in Oracle Cloud Console allow TCP ports 5173 and 8000).*

5. **Start ULPF**:
   ```bash
   docker compose up -d --build
   ```
   Your platform is now accessible at `http://<YOUR_SERVER_PUBLIC_IP>:5173`!

---

## 7. Host Log Connectors (Windows, Linux, macOS)

ULPF features native cross-platform agent connectors to stream real-time operating system logs into the platform.

### Downloadable from Dashboard:
Navigate to **Live Stream & Agents** (`/telemetry` tab `connectors`) to download pre-packaged bundle scripts for:
- **Windows**: Windows Event Log Tailer (Security, System, Application event channels).
- **Linux**: `systemd-journald` and `/var/log/auth.log`, `syslog` streaming agent.
- **macOS**: `log stream` / `/var/log/system.log` streaming agent.

### Quick Run from Repository:
```cmd
# Windows (Run as Administrator)
scripts\ulpf-connector\run_connector.bat

# Linux / macOS
cd backend/app/connector_bundle
python connector.py
```

---

## 8. Platform Architecture & Workspaces

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ULPF SecOps Platform                            │
├────────────────────────────────────────────────────────────────────────┤
│ 1. SOC Command Center        │ Real-time HUD, KPI counters, risk triage│
│ 2. Live Telemetry & Agents   │ SSE live stream, native OS connectors   │
│ 3. Discovery & Ingestion     │ Parser detection, drag-drop, CSE map    │
│ 4. Log Pipeline & Schema     │ Drift detector, quarantine, log replay  │
│ 5. Threat Detection & Intel  │ MITRE ATT&CK matrix, correlation engine │
│ 6. Forensics & Audit Ledger  │ WORM evidence, SHA-256 integrity chain │
│ 7. Platform Admin & Lab      │ 11 attack simulations, cluster settings │
└────────────────────────────────────────────────────────────────────────┘
```

### Multi-Tenant Cryptographic Chain of Custody:
- Every action (ingestion, rule edit, incident update, export) commits to an immutable SHA-256 audit ledger.
- Each tenant workspace maintains an independent, tamper-evident hash chain starting from its own Genesis block (`prev_hash=""`).
- Tampering with any historical audit entry immediately breaks the chain and is flagged during verification.

---

## 9. Troubleshooting & FAQs

### Q: Port 5173 or 8000 is already in use
**A:** Run cleanup or identify the offending process:
```powershell
# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Linux / macOS
lsof -i :5173
kill -9 <PID>
```

### Q: Docker fails with `IsADirectoryError: /app/.env.live`
**A:** If Docker previously created `.env` as a directory when it was missing:
```powershell
# In PowerShell:
Remove-Item -Recurse -Force .env
Copy-Item .env.example .env
docker compose down
docker compose up -d
```

### Q: How do I completely wipe and start fresh?
```bash
# Docker fresh start
docker compose down -v
docker compose up -d --build
```

### Q: Do I need internet access or paid API keys?
**A:** **No.** All threat simulation, parsing, correlation, MITRE ATT&CK mapping, and cryptographic auditing function **100% offline**. Third-party enrichment APIs (VirusTotal, AbuseIPDB) are completely optional and can be toggled in **Platform Lab → Live Settings**.

---

<div align="center">
  <sub>Built with pride for Smart India Hackathon 2026 by <b>Team BEETLES</b>.</sub>
</div>
