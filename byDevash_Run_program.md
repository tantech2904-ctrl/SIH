# ULPF: Run the Project Manually on Windows

This guide explains how to start and stop the ULPF project without Docker.

## Prerequisites

Install these applications:

- Python 3.14 or a compatible Python version
- Node.js and npm

The backend uses SQLite for a manual local run, so PostgreSQL, Redis, and MinIO are not required for the basic application.

## Start the Project

Open **two PowerShell terminals** in the project root:

```powershell
cd E:\SIH\SIH
```

### 1. Start the backend

In the first terminal:

```powershell
cd E:\SIH\SIH\backend
& "C:\Program Files\Python314\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal open. The backend will be available at:

- API: http://localhost:8000
- Swagger API documentation: http://localhost:8000/docs

### 2. Start the frontend

In the second terminal:

```powershell
cd E:\SIH\SIH\frontend
npm.cmd run dev
```

Keep this terminal open. Open the application at:

- http://localhost:5173/

The frontend automatically proxies `/api` requests to the backend on port `8000`.

## Default Login Credentials

Use the following administrator account:

```text
Email: admin@ulpf.local
Password: ChangeMe_Admin123!
```

Other bootstrap accounts:

```text
Analyst email: analyst@ulpf.local
Analyst password: ChangeMe_Analyst123!

Auditor email: auditor@ulpf.local
Auditor password: ChangeMe_Auditor123!
```

These are development credentials. Change them before using the project in a real environment.

## Stop the Project

To stop either service while the PC is running, go to its terminal and press:

```text
Ctrl+C
```

Stop both terminals:

1. Press `Ctrl+C` in the frontend terminal.
2. Press `Ctrl+C` in the backend terminal.

Closing the PowerShell windows also stops the processes, but `Ctrl+C` is the cleaner method.

## If a Port Is Already in Use

Check which process is using a port:

```powershell
Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue |
  Select-Object LocalPort,OwningProcess
```

Stop a process by its process ID if necessary:

```powershell
Stop-Process -Id <PROCESS_ID> -Force
```

Then start the backend and frontend again using the commands above.

## First-Time Installation

The frontend dependencies are installed from the `frontend` directory:

```powershell
cd E:\SIH\SIH\frontend
npm.cmd install
```

For Python 3.14, install the backend dependencies using compatible current releases:

```powershell
cd E:\SIH\SIH\backend
& "C:\Program Files\Python314\python.exe" -m pip install fastapi "uvicorn[standard]" pydantic pydantic-settings SQLAlchemy "psycopg[binary]" alembic "python-jose[cryptography]" "passlib[bcrypt]" bcrypt python-multipart redis celery minio httpx defusedxml xmltodict python-dateutil email-validator slowapi structlog requests python-evtx
& "C:\Program Files\Python314\python.exe" -m pip install --force-reinstall bcrypt==4.0.1
```

The second command keeps Passlib compatible with the project's password hashing code.

## Backend API Docs

The backend provides interactive API documentation after the backend terminal is running:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI specification: http://localhost:8000/openapi.json

Swagger UI lets you browse the available API endpoints, view request and response formats,
and try API calls directly from the browser. ReDoc provides a read-only reference that is
useful for browsing the API structure. The OpenAPI specification is the machine-readable
JSON definition of the complete backend API.

Some protected endpoints require authentication. Use the login endpoint in Swagger UI first,
then provide the returned bearer token using the **Authorize** button before testing those
endpoints.
