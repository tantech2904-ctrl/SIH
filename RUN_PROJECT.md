# ULPF Project Run Guide

This guide explains how to restart and stop the project on Windows after closing VS Code or shutting down the laptop.

## Prerequisites

Complete the one-time setup first:

- Python is installed.
- Node.js and npm are installed.
- Backend dependencies are installed in `backend\venv`.
- Frontend dependencies are installed in `frontend\node_modules`.

You do not need to reinstall dependencies every time you restart the project.

## Start the Project

Start the backend and frontend in two separate PowerShell terminals.

### 1. Start the backend

Open PowerShell and run:

```powershell
Set-Location E:\SIH\SIH\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal open while using the project.

### 2. Start the frontend

Open a second PowerShell terminal and run:

```powershell
Set-Location E:\SIH\SIH\frontend
npm.cmd run dev
```

Keep this terminal open as well.

### 3. Open the project

Open these URLs in your browser:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API health check: http://localhost:8000/api/v1/health
- Swagger API documentation: http://localhost:8000/docs

The health check should return a response containing `"status":"ok"`.

## Stop the Project

In the backend terminal, press:

```text
Ctrl+C
```

Then press `Ctrl+C` in the frontend terminal.

After both commands finish, you can close the terminals or close VS Code. Your project files and SQLite database remain on disk.

## After Shutting Down the Laptop

When you start the laptop again:

1. Open VS Code.
2. Open the folder `E:\SIH\SIH`.
3. Open one PowerShell terminal for the backend.
4. Open a second PowerShell terminal for the frontend.
5. Run the start commands from this guide.
6. Open http://localhost:5173.

The project does not start automatically after Windows restarts. You must run both commands again.

## First-Time Setup Only

Use these commands only if the virtual environment or frontend dependencies do not exist yet.

### Backend dependencies

```powershell
Set-Location E:\SIH\SIH\backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Frontend dependencies

```powershell
Set-Location E:\SIH\SIH\frontend
npm.cmd ci
npm.cmd run build
```

## Troubleshooting

### Port 8000 or 5173 is already in use

Find the process using a port:

```powershell
Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue |
    Select-Object LocalPort,OwningProcess
```

Stop a process only after confirming its process ID:

```powershell
Stop-Process -Id <PROCESS_ID> -Force
```

Then run the backend and frontend start commands again.

### PowerShell blocks npm

Use `npm.cmd` instead of `npm`:

```powershell
npm.cmd run dev
```

### Backend dependencies appear missing

Confirm that the backend virtual environment exists:

```powershell
Test-Path E:\SIH\SIH\backend\venv\Scripts\python.exe
```

If the result is `False`, run the first-time backend setup commands above.
