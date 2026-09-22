# ULPF — Universal Log Pre-processing Framework

ULPF can be run locally using **Docker Compose** (recommended) or configured **manually** for development.

## 🐳 Quick Start (Docker)

**Prerequisites:** Docker and Docker Compose.

1. Open your terminal and navigate to the project root:
```bash
cd ULPF

```


2. Build and start the stack:
```bash
docker compose up --build

```


3. To stop the project, press `Ctrl + C` or run `docker compose down`.

---

## 🌐 Service URLs

Once the services are running, access them via your browser:

| Service | URL | Credentials |
| --- | --- | --- |
| **Frontend** | http://localhost:5173 | - |
| **Backend API** | http://localhost:8000 | - |
| **API Health Check** | http://localhost:8000/api/v1/health | - |
| **Swagger API Docs** | http://localhost:8000/docs | - |
| **MinIO Console** | http://localhost:9001 | **User:** `ulpfadmin` <br>

<br> **Pass:** `ulpfadminsecret` |

*Note: Change MinIO credentials before any real deployment.*

---

## 🛠 Manual Local Setup

If you prefer not to use Docker, install **Python 3.11+**, **Node.js 18+**, and **npm**. The local backend uses SQLite by default, so Postgres, Redis, and MinIO are not required for the basic API and frontend workflow. Run the backend and frontend in separate PowerShell windows.

### Terminal 1: Backend (PowerShell)

Run these commands from the repository root:

```powershell
Set-Location E:\SIH\SIH\backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The virtual environment does not need to be activated when its Python executable is called directly. If you prefer to activate it, run `.\venv\Scripts\Activate.ps1` first and then use `python` for the remaining commands. If PowerShell blocks activation, continue using the direct executable commands above.

### Terminal 2: Frontend (PowerShell)

Run these commands from the repository root in a second terminal:

```powershell
Set-Location E:\SIH\SIH\frontend
npm.cmd ci
npm.cmd run build
npm.cmd run dev
```

`npm.cmd` is used because PowerShell may block the `npm.ps1` wrapper when script execution is restricted. The Vite development server proxies `/api` requests to the backend at `http://localhost:8000`.

### Verify the local setup

Open these URLs after both terminals are running:

| Service | URL |
| --- | --- |
| **Frontend** | http://localhost:5173 |
| **Backend** | http://localhost:8000 |
| **API Health Check** | http://localhost:8000/api/v1/health |
| **Swagger API Docs** | http://localhost:8000/docs |

To stop either service, press `Ctrl+C` in its terminal. The SQLite database is created automatically in `backend/ulpf.db` on first backend startup.

### Optional: run with Docker services locally

If you need Postgres, Redis, or MinIO for features that depend on them, start the infrastructure services from the repository root:

```powershell
Set-Location E:\SIH\SIH
Copy-Item .env.example .env
docker compose up -d postgres redis minio
```

The Docker Compose backend uses its own container-specific connection settings. For the manual backend, keep the default SQLite configuration unless you intentionally configure local connection URLs.

---

## 🧪 Running Backend Tests

ULPF includes an API test suite using `pytest`. Ensure your virtual environment is active and run the following from the backend directory:

```bash
cd ULPF/backend
python -m pytest -q

```

---

## 📂 Project Structure

* **`backend/`**: FastAPI application, including routes (`app/api/`), parsers (`app/parsers/`), and tests (`tests/`).
* **`frontend/`**: React application source (`src/`) and assets.
* **`docker-compose.yml`**: Docker service configurations.
* **`samples/`**: Sample security logs for testing.

---

## ⚠️ Troubleshooting

* **Port already in use:** If ports `8000`, `5173`, or `9001` are occupied, stop the conflicting service before starting ULPF.
* **Backend dependencies or pytest fails:** Ensure you are in the `ULPF/backend/` directory and your virtual environment (`venv`) is activated.
* **Docker services won't start:** Try forcing a clean rebuild without cache:
```bash
docker compose down
docker compose build --no-cache
docker compose up

```