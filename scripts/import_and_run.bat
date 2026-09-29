@echo off
setlocal EnableDelayedExpansion
title ULPF SIEM - SIH Demo Launcher
color 0B
chcp 65001 >nul 2>&1

cls
echo.
echo   ============================================================
echo.
echo        U L P F   S I E M
echo        Universal Log Pre-Processing Framework
echo        Smart India Hackathon 2024 - Live Demo
echo.
echo   ============================================================
echo.

:: ── Docker Desktop check ─────────────────────────────────────────
docker --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo   [ERROR] Docker Desktop not found on this machine.
    echo.
    echo           Download it at:
    echo           https://www.docker.com/products/docker-desktop/
    echo.
    echo           After installing: start Docker Desktop, wait for the
    echo           whale icon in the taskbar, then run this script again.
    echo.
    pause
    exit /b 1
)

:: ── Locate image archive ─────────────────────────────────────────
set "IMAGES=%~dp0ulpf-sih-demo-images.tar"
if not exist "!IMAGES!" set "IMAGES=%~dp0..\ulpf-sih-demo-images.tar"
if not exist "!IMAGES!" (
    color 0C
    echo   [ERROR] ulpf-sih-demo-images.tar not found.
    echo.
    echo           It should be in the same folder as this script.
    echo           Folder: %~dp0
    echo.
    pause
    exit /b 1
)

:: ── Load images (skip if already loaded) ─────────────────────────
docker image inspect ulpf-backend:demo >nul 2>&1
if errorlevel 1 (
    echo   [*] Loading ULPF images from archive...
    echo       This takes 3-5 minutes on first run. Please wait.
    echo.
    docker load -i "!IMAGES!"
    if errorlevel 1 (
        color 0C
        echo.
        echo   [ERROR] docker load failed.
        echo           The archive may be corrupted. Re-export with export_demo.bat.
        echo.
        pause
        exit /b 1
    )
    echo   [OK] Images loaded successfully.
    echo.
) else (
    echo   [OK] Images already loaded - skipping import ^(fast start^).
    echo.
)

:: ── Navigate to project root ──────────────────────────────────────
set "SCRIPTS_DIR=%~dp0"
if "!SCRIPTS_DIR:~-1!"=="\" set "SCRIPTS_DIR=!SCRIPTS_DIR:~0,-1!"
for %%I in ("!SCRIPTS_DIR!\..") do set "REPO_ROOT=%%~fI"
cd /d "!REPO_ROOT!"

:: ── Copy .env.docker → .env ───────────────────────────────────────
if exist "scripts\.env.docker" (
    copy /Y "scripts\.env.docker" ".env" >nul
    echo   [OK] Environment configured for Docker mode.
)

:: ── Start the stack ───────────────────────────────────────────────
echo   [*] Starting ULPF SIEM...
docker compose up -d --remove-orphans
if errorlevel 1 (
    color 0E
    echo.
    echo   [!!] docker compose up failed.
    echo.
    echo        Common causes:
    echo          - Docker Desktop not fully started ^(wait 30s and retry^)
    echo          - Port conflict on 5173 / 8000 / 5432 / 6379 / 9000
    echo            ^(run: netstat -ano ^| findstr "5173 8000 5432"^)
    echo.
    echo        Diagnostics:  docker compose ps
    echo        Logs:         docker compose logs backend
    echo.
    pause
    exit /b 1
)

:: ── Wait for readiness ────────────────────────────────────────────
echo   [*] Waiting for services to start...
set /a TICKS=0
:WAIT_LOOP
set /a TICKS+=1
if !TICKS! GTR 90 goto WAIT_TIMEOUT
timeout /t 3 /nobreak >nul
set /a PCT=!TICKS!*100/90
if !PCT! GTR 99 set /a PCT=99
<nul set /p ="    Startup: !PCT!%%    " & echo.& <nul set /p ".">nul 2>&1
powershell -NoProfile -Command ^
    "try{Invoke-WebRequest http://localhost:5173 -UseBasicParsing -TimeoutSec 2|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 goto WAIT_LOOP
powershell -NoProfile -Command ^
    "try{Invoke-WebRequest http://localhost:8000/api/v1/health/ready -UseBasicParsing -TimeoutSec 2|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 goto WAIT_LOOP
goto READY

:WAIT_TIMEOUT
color 0E
echo.
echo   [!!] Services did not start within 4.5 minutes.
echo.
echo        Diagnostics:
docker compose ps
echo.
echo        Run: docker compose logs backend   to see errors.
echo.
pause
exit /b 1

:READY
start "" "http://localhost:5173"

cls
echo.
echo   ============================================================
echo.
echo        ULPF SIEM is running!
echo.
echo        Open in browser:  http://localhost:5173
echo        API Docs:         http://localhost:8000/docs
echo        Storage UI:       http://localhost:9001  ^(ulpfadmin / ulpfadminsecret^)
echo.
echo   ============================================================
echo.
echo     Demo Credentials:
echo.
echo       [Admin]    admin@ulpf.local     ChangeMe_Admin123!   ^<-- Start here
echo       [Analyst]  analyst@ulpf.local   ChangeMe_Analyst123!
echo       [Auditor]  auditor@ulpf.local   ChangeMe_Auditor123!
echo.
echo     Platform Capabilities:
echo       - 6 Unified Workspaces: Command Center, Telemetry, Discovery,
echo         Pipeline Normalization, MITRE ATT&CK Detection, Forensic Evidence
echo       - ML Training Dataset Export ^(JSONL / CSV / JSON up to 10k records^)
echo       - Plug-and-Play Parsers, Field Mappings, and Quarantine Replay
echo.
echo     Quick Demo:
echo       1.  Log in as Admin  ^(recommended for full feature access^)
echo       2.  Click [Site Tour] in top bar for interactive guided walkthrough
echo       3.  Click [Run Demo] on Dashboard to fire 11 attack scenarios live
echo       4.  Inspect Live Stream SSE telemetry and Event Explorer datasets
echo.
echo   ============================================================
echo.
echo     Commands  ^(press key in this window^):
echo       S   status          L   backend logs
echo       A   all logs        O   open browser
echo       Q   quit ^& stop ULPF
echo.
:CONSOLE
choice /c slaboq /n /t 60 /d s /m "ulpf-demo^> " >nul 2>&1
set "CE=!ERRORLEVEL!"
if "!CE!"=="1" (
    echo.
    docker compose ps
    echo.
    goto CONSOLE
)
if "!CE!"=="2" (
    echo.
    docker compose logs --tail=25 backend 2>&1
    echo.
    goto CONSOLE
)
if "!CE!"=="3" (
    echo.
    docker compose logs --tail=25 2>&1
    echo.
    goto CONSOLE
)
if "!CE!"=="4" (
    docker compose logs --tail=25 2>&1
    echo.
    goto CONSOLE
)
if "!CE!"=="5" (
    start "" "http://localhost:5173"
    goto CONSOLE
)
if "!CE!"=="6" goto SHUTDOWN
goto CONSOLE

:SHUTDOWN
echo.
echo   Stopping ULPF SIEM...
docker compose down
color 0A
echo   Done. Goodbye!
echo.
timeout /t 2 /nobreak >nul
exit /b 0
