@echo off
setlocal EnableDelayedExpansion EnableExtensions
title ULPF Docker
color 0B

:: ============================================================
::  ULPF - Docker Worker
::
::  Called by start_ulpf.bat after the connector is installed.
::  Responsibilities:
::    1. Write .env from scripts\.env.docker
::    2. docker compose up -d
::    3. Wait for services to be healthy
::    4. Open browser, enter control console
:: ============================================================

set "SCRIPTS_DIR=%~dp0"
if "!SCRIPTS_DIR:~-1!"=="\" set "SCRIPTS_DIR=!SCRIPTS_DIR:~0,-1!"
for %%I in ("!SCRIPTS_DIR!\..") do set "REPO_ROOT=%%~fI"

set "ULPF_HOME=%USERPROFILE%\.ulpf"
set "INSTALL_LOG=%ULPF_HOME%\install.log"

set "ENV_TEMPLATE=!SCRIPTS_DIR!\.env.docker"
set "ENV_TARGET=!REPO_ROOT!\.env"

:: ============================================================
:: 1. Write .env for Docker
:: ============================================================
cls
echo.
echo   ============================================================
echo.
echo        U L P F   -   D O C K E R   M O D E
echo.
echo   ============================================================
echo.
call :say "Preparing .env for Docker..."

if not exist "!ENV_TEMPLATE!" goto NO_TEMPLATE

:: Back up existing .env
if exist "!ENV_TARGET!" (
    set "TS="
    for /f "usebackq tokens=*" %%T in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd-HHmmss'"`) do set "TS=%%T"
    if "!TS!"=="" set "TS=backup"
    move /Y "!ENV_TARGET!" "!ENV_TARGET!.bak.!TS!" >nul
    echo          [OK] Backed up old .env to .env.bak.!TS!
)

copy /Y "!ENV_TEMPLATE!" "!ENV_TARGET!" >nul
echo          [OK] .env written from scripts\.env.docker

:: ============================================================
:: 2. Start Docker stack
:: ============================================================
cd /d "!REPO_ROOT!"

call :say "Running docker compose up -d --remove-orphans..."
docker compose up -d --remove-orphans
set "DC_EXIT=!ERRORLEVEL!"
if not "!DC_EXIT!"=="0" goto DOCKER_FAIL

echo          [OK] Docker stack started.

:: ============================================================
:: 3. Wait for readiness
:: ============================================================
call :say "Waiting for services to become healthy..."
call :wait_for_ready
if errorlevel 1 goto WAIT_TIMEOUT

:: ============================================================
:: 4. Control console
:: ============================================================
goto CONTROL_LOOP

:NO_TEMPLATE
color 0C
echo.
echo          ERROR: scripts\.env.docker not found.
echo.
pause
exit /b 1

:DOCKER_FAIL
color 0E
echo.
echo          [!!] docker compose up failed.
echo.
echo          Common causes:
echo            - Docker Desktop is not running
echo            - Ports 5173, 8000, 5432, 6379, 9000 in use
echo            - WSL2 needs updating  ^(wsl --update^)
echo.
pause
exit /b 1

:WAIT_TIMEOUT
color 0E
echo.
echo          [!!] Services did not become ready within 300s.
echo.
echo          Diagnostics:
docker compose ps
echo.
pause
exit /b 1

:: ============================================================
:: CONTROL LOOP
:: ============================================================
:CONTROL_LOOP
echo.
echo          Opening browser...
start "" "http://localhost:5173"

:CONTROL_TICK
choice /c qslohrbc /n /t 5 /d s /m "ulpf-docker> " >nul 2>&1
set "CE=!ERRORLEVEL!"

if "!CE!"=="1" goto SHUTDOWN
if "!CE!"=="2" call :CTL_STATUS
if "!CE!"=="3" call :CTL_LOGS
if "!CE!"=="4" start "" "http://localhost:5173"
if "!CE!"=="5" call :CTL_HELP
if "!CE!"=="6" call :CTL_RESTART
if "!CE!"=="7" call :CTL_REBUILD
if "!CE!"=="8" cls & call :draw_console
goto CONTROL_TICK

:CTL_STATUS
call :draw_console
goto CONTROL_TICK

:CTL_LOGS
cls
echo.
echo   ----- Last 30 lines: backend -----
docker compose logs --tail=30 backend 2>&1
echo.
echo   Press any key...
pause >nul
call :draw_console
goto CONTROL_TICK

:CTL_HELP
cls
echo.
echo   s - status   l - logs   o - open browser
echo   h - help     r - restart stack
echo   b - rebuild  c - clear  q - quit
echo.
pause >nul
call :draw_console
goto CONTROL_TICK

:CTL_RESTART
echo.
echo   Restarting stack...
docker compose restart
timeout /t 2 /nobreak >nul
call :draw_console
goto CONTROL_TICK

:CTL_REBUILD
echo.
set /p "RBOK=   Rebuild images from scratch? [y/N]: "
if /i not "!RBOK!"=="y" goto CONTROL_TICK
docker compose build --no-cache backend worker frontend
if errorlevel 1 (
    echo   Build failed.
    pause
    goto CONTROL_TICK
)
docker compose up -d --remove-orphans
timeout /t 2 /nobreak >nul
call :draw_console
goto CONTROL_TICK

:SHUTDOWN
color 0E
cls
echo.
echo   Stopping Docker stack...
docker compose down
color 0A
echo.
echo   ULPF stopped. Closing in 3 seconds.
timeout /t 3 /nobreak >nul
exit

:: ============================================================
:: HELPERS
:: ============================================================
:say
echo   [*] %~1
exit /b 0

:wait_for_ready
set /a TICKS=0
set /a MAX=150

:WFR_LOOP
set /a TICKS+=1
if !TICKS! GTR %MAX% exit /b 1

powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto WFR_DRAW

powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto WFR_DRAW

exit /b 0

:WFR_DRAW
set /a PCT=!TICKS!*100/%MAX%
if !PCT! GTR 99 set /a PCT=99
set /a FILL=!PCT!/2
set "BAR="
for /l %%i in (1,1,!FILL!) do set "BAR=!BAR!#"
set /a SP=50-!FILL!
for /l %%i in (1,1,!SP!) do set "BAR=!BAR!."
cls
echo.
echo   ============================================================
echo     ULPF Docker is starting...
echo   ============================================================
echo.
echo     Progress: [!BAR!] !PCT!%%
echo.
timeout /t 2 /nobreak >nul
goto WFR_LOOP

:draw_console
cls
echo.
echo   ============================================================
echo                U L P F   D O C K E R   R U N N I N G
echo   ============================================================
echo.
echo     Frontend:    http://localhost:5173
echo     API Docs:    http://localhost:8000/docs
echo     Storage UI:  http://localhost:9001  ^(ulpfadmin / ulpfadminsecret^)
echo.
echo     Login:       admin@ulpf.local / ChangeMe_Admin123!
echo.
echo   ------------------------------------------------------------
echo     Workspaces:
echo       1. SOC Command Center       4. Pipeline & Schema Normalization
echo       2. Live Telemetry & Streams 5. Threat Detection & MITRE ATT&CK
echo       3. Discovery & ML Export    6. Forensic Evidence & Audit
echo   ------------------------------------------------------------
echo     Commands:
echo       s   status       l   logs          o   open browser
echo       h   help         r   restart       b   rebuild images
echo       c   clear        q   quit & stop
echo.
exit /b 0