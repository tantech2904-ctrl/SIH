@echo off
setlocal EnableDelayedExpansion EnableExtensions
title ULPF Control
color 0B
chcp 65001 >nul 2>&1

:: ============================================================
::  ULPF - Universal Log Pre-Processing Framework
::  Fully automatic setup + control console.
::
::  Just double-click this file. It will:
::    1. Request Administrator (UAC prompt - accept it)
::    2. Ask which mode to run in (Docker / Local)
::    3. Validate prerequisites for that mode
::    4. Prepare and validate .env
::    5. Install & start the host log connector service
::    6. Start the stack
::    7. Open the browser
::    8. Stay open as a control console (type q to quit)
::
::  Supported Python: 3.10, 3.11, 3.12 only.
::  If multiple versions are installed, the newest supported one
::  is picked automatically via the py launcher.
::
::  Safe to re-run. Idempotent.
:: ============================================================

:: ============================================================
:: ELEVATION  (cmd-only redirects — do NOT invoke PowerShell here)
:: ============================================================
net session >nul 2>&1
if errorlevel 1 goto ELEVATE
goto ELEVATED

:ELEVATE
cls
echo.
echo   ============================================================
echo.
echo        U L P F   -   E L E V A T I O N   R E Q U I R E D
echo.
echo   ============================================================
echo.
echo     ULPF needs Administrator privileges to install and
echo     manage the host log connector service.
echo.
echo     A UAC prompt will appear. Accept it to continue.
echo.
echo   ------------------------------------------------------------
echo     Requesting elevation...
echo   ------------------------------------------------------------
echo.
timeout /t 2 /nobreak >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
exit /b 0

:ELEVATED

:: -------------------- Parse args --------------------
set "ARG_RESET_ENV=0"
set "ARG_REBUILD=0"
set "ARG_NO_CONNECTOR=0"
set "ARG_AUTO=1"
set "ARG_MODE="
for %%A in (%*) do call :parse_arg "%%~A"

:: -------------------- Repo root --------------------
set "REPO_ROOT=%~dp0"
if "!REPO_ROOT:~-1!"=="\" set "REPO_ROOT=!REPO_ROOT:~0,-1!"
cd /d "!REPO_ROOT!"

:: -------------------- State directories --------------------
set "ULPF_HOME=%USERPROFILE%\.ulpf"
if not exist "%ULPF_HOME%" mkdir "%ULPF_HOME%" >nul 2>&1
set "INSTALL_LOG=%ULPF_HOME%\install.log"
set "INSTALL_MARKER=%ULPF_HOME%\install-marker.json"

:: SYSTEM-readable connector config directory (created with admin rights)
set "CONNECTOR_DATA_DIR=C:\ProgramData\ULPF"
set "CONNECTOR_CONFIG=!CONNECTOR_DATA_DIR!\connector.json"

set "MODE="
set "DOCKER_OK=0"
set "PY_VER="
set "PY_LAUNCHER="
set "NODE_VER="
set "FIRST_RUN=true"
set "LAST_CHECK=ok"
set "CONNECTOR_STATE=unknown"
set "SVC_LINE="
set "SVC_RC="
set "SVC_CACHE_TS=0"

:: ============================================================
:: HEADER
:: ============================================================
call :draw_header
echo.
echo       This will prepare and start ULPF on your computer.
echo       Nothing outside this folder and your user profile
echo       will be modified.
echo.
echo       Running elevated: connector service will be managed.
echo.
call :log "===== ULPF setup starting ====="
call :log "Repo root: !REPO_ROOT!"

if exist "%INSTALL_MARKER%" set "FIRST_RUN=false"

:: ============================================================
:: STEP 1 - MODE SELECTION  (asked first, before any checks)
:: ============================================================
:STEP_MODE
if not "!ARG_MODE!"=="" (
    set "CHOICE=!ARG_MODE!"
    goto MODE_RESOLVE
)

call :draw_mode_menu
set /p "CHOICE=          Enter choice [1/2/3]: "

:MODE_RESOLVE
if "!CHOICE!"=="1" goto MODE_TRY_DOCKER
if "!CHOICE!"=="2" goto MODE_TRY_LOCAL
if "!CHOICE!"=="3" goto MODE_EXIT
if /i "!CHOICE!"=="docker" goto MODE_TRY_DOCKER
if /i "!CHOICE!"=="local"  goto MODE_TRY_LOCAL
if /i "!CHOICE!"=="exit"   goto MODE_EXIT
echo.
echo          Invalid choice. Please enter 1, 2, or 3.
timeout /t 2 /nobreak >nul
set "CHOICE="
goto STEP_MODE

:MODE_EXIT
echo.
echo          Exiting setup.
exit /b 0

:MODE_TRY_DOCKER
set "MODE=docker"
call :log "Mode selected: docker"
goto MODE_VALIDATE_DOCKER

:MODE_TRY_LOCAL
set "MODE=local"
call :log "Mode selected: local"
goto MODE_VALIDATE_LOCAL

:: ------------------------------------------------------------
:: Mode validation — Docker
:: ------------------------------------------------------------
:MODE_VALIDATE_DOCKER
call :draw_step 1 "Validating Docker mode"
echo.
call :check_docker
echo.
if "!DOCKER_OK!"=="1" goto MODE_LOCKED

color 0E
echo          [!!] Docker is not available on this system.
echo.
echo          Options:
echo            [1]  Open the Docker Desktop download page
echo            [2]  Go back and choose LOCAL mode instead
echo            [3]  Exit setup
echo.
set /p "DRCHOICE=          Enter choice [1/2/3]: "
if "!DRCHOICE!"=="1" goto CHOICE_INSTALL_DOCKER
if "!DRCHOICE!"=="2" goto STEP_MODE
echo          Exiting setup.
exit /b 0

:CHOICE_INSTALL_DOCKER
echo.
echo          Opening Docker Desktop download page...
start "" "https://www.docker.com/products/docker-desktop/"
echo.
echo          After installing Docker Desktop and restarting,
echo          run this file again.
echo.
pause
exit /b 0

:: ------------------------------------------------------------
:: Mode validation — Local
:: ------------------------------------------------------------
:MODE_VALIDATE_LOCAL
call :draw_step 1 "Validating local mode"
echo.
call :check_python
call :check_node
echo.
if "!PY_LAUNCHER!"=="" goto LOCAL_NO_PY
if "!NODE_VER!"==""    goto LOCAL_NO_NODE
goto MODE_LOCKED

:LOCAL_NO_PY
color 0C
echo          [!!] Local mode requires Python 3.10, 3.11, or 3.12.
echo               Python 3.13+ is not yet supported.
echo.
echo               Install Python 3.12 from:
echo                 https://www.python.org/downloads/release/python-3129/
echo               Check "Add Python to PATH" during install.
echo.
echo            [1]  Go back and choose DOCKER mode
echo            [2]  Exit setup
echo.
set /p "LRCHOICE=          Enter choice [1/2]: "
if "!LRCHOICE!"=="1" goto STEP_MODE
exit /b 1

:LOCAL_NO_NODE
color 0C
echo          [!!] Local mode requires Node 18 or newer.
echo               Install Node from https://nodejs.org/
echo.
echo            [1]  Go back and choose DOCKER mode
echo            [2]  Exit setup
echo.
set /p "LRCHOICE=          Enter choice [1/2]: "
if "!LRCHOICE!"=="1" goto STEP_MODE
exit /b 1

:MODE_LOCKED
echo.
echo          Mode locked: !MODE!
echo.
timeout /t 1 /nobreak >nul

:: ============================================================
:: STEP 2 - ENV FILE
:: ============================================================
call :draw_step 2 "Preparing environment file"
echo.

call :pick_template
call :maybe_backup_env
call :ensure_env_exists
call :validate_env_critical
call :validate_env_for_mode
call :validate_migrations
call :rotate_env_backups

echo.
timeout /t 1 /nobreak >nul
goto STEP_CONNECTOR

:pick_template
set "TEMPLATE=!REPO_ROOT!\.env.example"
if not "!MODE!"=="local" exit /b 0
if not exist "!REPO_ROOT!\scripts\.env.local.example" goto PICK_TEMPLATE_FALLBACK
set "TEMPLATE=!REPO_ROOT!\scripts\.env.local.example"
call :log "Using local-mode template"
exit /b 0

:PICK_TEMPLATE_FALLBACK
color 0E
echo          [!!] scripts\.env.local.example not found.
echo          [!!] Falling back to .env.example.
call :log "WARN: local template missing, using .env.example"
exit /b 0

:maybe_backup_env
if not "!ARG_RESET_ENV!"=="1" exit /b 0
if not exist "!REPO_ROOT!\.env" exit /b 0
for /f "tokens=1-6 delims=/:. " %%a in ("%DATE% %TIME%") do set "TS=%%c-%%a-%%b-%%d-%%e-%%f"
move /Y "!REPO_ROOT!\.env" "!REPO_ROOT!\.env.bak.!TS!" >nul
echo          Backed up existing .env to .env.bak.!TS! ^(--reset-env^)
call :log "Backed up .env (reset-env)"
exit /b 0

:ensure_env_exists
if not exist "!TEMPLATE!" goto ENSURE_ENV_NO_TEMPLATE
if exist "!REPO_ROOT!\.env" goto ENSURE_ENV_ALREADY
copy /Y "!TEMPLATE!" "!REPO_ROOT!\.env" >nul
if errorlevel 1 goto ENSURE_ENV_COPY_FAIL
echo          [OK] .env created from template.
call :log ".env created from template"
if "!MODE!"=="docker" call :patch_env_for_docker
exit /b 0

:ENSURE_ENV_ALREADY
echo          [OK] .env exists - leaving untouched.
echo               ^(pass --reset-env to regenerate^)
call :log ".env preserved (already exists)"
exit /b 0

:ENSURE_ENV_NO_TEMPLATE
color 0C
echo.
echo          ERROR: Template not found at !TEMPLATE!
call :log "FATAL: template missing"
pause
exit /b 1

:ENSURE_ENV_COPY_FAIL
color 0C
echo          ERROR: Failed to create .env from template.
call :log "FATAL: could not copy template"
pause
exit /b 1

:: ------------------------------------------------------------
:: Validate .env has required vars; auto-fill Postgres if missing.
:: ------------------------------------------------------------
:validate_env_critical
set "ENV_CHANGED=0"

for %%V in (POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB) do (
    findstr /B /C:"%%V=" "!REPO_ROOT!\.env" >nul 2>&1
    if errorlevel 1 (
        echo          [!!] Missing %%V - adding default.
        echo %%V=ulpf>>"!REPO_ROOT!\.env"
        set "ENV_CHANGED=1"
    )
)

:: Catch empty POSTGRES_PASSWORD (allowing trailing spaces)
findstr /R /C:"^POSTGRES_PASSWORD= *$" "!REPO_ROOT!\.env" >nul 2>&1
if not errorlevel 1 (
    echo          [!!] POSTGRES_PASSWORD is empty - fixing.
    powershell -NoProfile -Command ^
        "(Get-Content -Raw '!REPO_ROOT!\.env') -replace 'POSTGRES_PASSWORD=\s*\r?\n','POSTGRES_PASSWORD=ulpf`n' | Set-Content -NoNewline '!REPO_ROOT!\.env'"
    set "ENV_CHANGED=1"
)

if "!ENV_CHANGED!"=="1" (
    echo          [OK] .env patched with required values.
    call :log ".env auto-patched with missing POSTGRES_* vars"
)
exit /b 0

:: ------------------------------------------------------------
:: Validate .env matches the chosen mode.
:: ------------------------------------------------------------
:validate_env_for_mode
if "!MODE!"=="docker" goto VALIDATE_MODE_DOCKER
if "!MODE!"=="local" goto VALIDATE_MODE_LOCAL
exit /b 0

:VALIDATE_MODE_LOCAL
findstr /C:"@postgres:" "!REPO_ROOT!\.env" >nul 2>&1
if not errorlevel 1 goto VALIDATE_MODE_LOCAL_FIX
findstr /C:"@redis:" "!REPO_ROOT!\.env" >nul 2>&1
if not errorlevel 1 goto VALIDATE_MODE_LOCAL_FIX
findstr /C:"MINIO_ENDPOINT=minio:" "!REPO_ROOT!\.env" >nul 2>&1
if not errorlevel 1 goto VALIDATE_MODE_LOCAL_FIX
exit /b 0

:VALIDATE_MODE_LOCAL_FIX
color 0E
echo.
echo          [!!] .env looks like it was set up for Docker
echo               ^(hostnames: postgres / redis / minio^).
echo               Local mode cannot resolve those hostnames.
echo.
echo               Fixing .env to use localhost...
powershell -NoProfile -Command ^
    "$p='!REPO_ROOT!\.env'; $c=Get-Content -Raw -LiteralPath $p; " ^
    "$c=$c -replace '@postgres:','@localhost:'; " ^
    "$c=$c -replace '@redis:','@localhost:'; " ^
    "$c=$c -replace 'MINIO_ENDPOINT=minio:','MINIO_ENDPOINT=localhost:'; " ^
    "Set-Content -LiteralPath $p -Value $c -NoNewline -Encoding UTF8"
echo          [OK] .env patched for local mode.
call :log "Local-mode .env had Docker hostnames; patched to localhost"
color 0B
exit /b 0

:VALIDATE_MODE_DOCKER
exit /b 0

:: ------------------------------------------------------------
:: Validate migrations don't contain unguarded create_all().
:: ------------------------------------------------------------
:validate_migrations
set "MIG_BAD=0"

if not exist "!REPO_ROOT!\backend\alembic\versions\0001_initial.py" exit /b 0

findstr /C:"insp.get_table_names" "!REPO_ROOT!\backend\alembic\versions\0001_initial.py" >nul 2>&1
if errorlevel 1 (
    findstr /C:"Base.metadata.create_all" "!REPO_ROOT!\backend\alembic\versions\0001_initial.py" >nul 2>&1
    if not errorlevel 1 set "MIG_BAD=1"
)

if "!MIG_BAD!"=="1" (
    color 0E
    echo.
    echo   ------------------------------------------------------------
    echo     WARNING: 0001_initial.py uses unguarded create_all().
    echo     This causes DuplicateTable errors on restart. Wrap it in
    echo     an existence check (see the fixed version in the repo).
    echo   ------------------------------------------------------------
    color 0B
    call :log "WARN: 0001_initial.py still has unguarded create_all()"
)
exit /b 0

:: ============================================================
:: STEP 3 - CONNECTOR SERVICE
:: ============================================================
:STEP_CONNECTOR
if "!ARG_NO_CONNECTOR!"=="1" goto CONNECTOR_SKIPPED
call :draw_step 3 "Host log connector"
echo.
:: Connector needs Python even in Docker mode
if "!PY_LAUNCHER!"=="" call :check_python
if "!PY_LAUNCHER!"=="" goto CONNECTOR_NO_PY
if not exist "!REPO_ROOT!\scripts\ulpf-connector\connector.py" goto CONNECTOR_NO_SCRIPTS
call :setup_connector_service
call :refresh_connector_state
goto AFTER_CONNECTOR

:CONNECTOR_SKIPPED
call :draw_step 3 "Host log connector"
echo.
echo          [--] Connector install skipped ^(--no-connector^).
set "CONNECTOR_STATE=skipped"
goto AFTER_CONNECTOR

:CONNECTOR_NO_PY
color 0E
echo          [--] Python 3.10 / 3.11 / 3.12 not found on host.
echo               The connector service requires it.
set "CONNECTOR_STATE=no-python"
call :log "Connector skipped: no supported host Python"
goto AFTER_CONNECTOR

:CONNECTOR_NO_SCRIPTS
color 0E
echo          [--] Connector scripts not found under scripts\ulpf-connector.
set "CONNECTOR_STATE=no-scripts"
call :log "Connector skipped: scripts missing"
goto AFTER_CONNECTOR

:AFTER_CONNECTOR
echo.
timeout /t 1 /nobreak >nul

:: ============================================================
:: STEP 4 - START SERVICES
:: ============================================================
call :draw_step 4 "Starting services"
echo.

if "!MODE!"=="docker" goto START_DOCKER
if "!MODE!"=="local" goto START_LOCAL
goto STEP_UNKNOWN_MODE

:STEP_UNKNOWN_MODE
color 0C
echo          ERROR: Unknown mode '!MODE!'. Exiting.
call :log "FATAL: unknown mode"
pause
exit /b 1

:: ------------------------------------------------------------
:: START - Docker
:: ------------------------------------------------------------
:START_DOCKER
call :log "Starting Docker stack"

set "NEED_REBUILD=0"
if "!ARG_REBUILD!"=="1" set "NEED_REBUILD=1"
if "!NEED_REBUILD!"=="0" call :detect_stale_build
if "!NEED_REBUILD!"=="1" call :docker_rebuild

echo          Running: docker compose up -d --remove-orphans
echo.
docker compose up -d --remove-orphans
set "DC_EXIT=!ERRORLEVEL!"
call :log "docker compose up exit code: !DC_EXIT!"

if not "!DC_EXIT!"=="0" goto DOCKER_UP_FAILED

echo.
echo          [OK] Docker containers started.
call :log "Docker stack started"
call :write_marker
goto WAIT_FOR_READY

:DOCKER_UP_FAILED
color 0E
echo.
echo          [!!] Docker Compose failed. See output above.
echo.
echo          Common causes:
echo            - Docker Desktop is not running
echo            - Ports 5173, 8000, 5432, 6379, 9000 are in use
echo            - WSL2 needs updating ^(run: wsl --update^)
echo.
echo            [1] Retry Docker Compose
echo            [2] Exit
echo.
set /p "RCHOICE=          Enter choice [1/2]: "
if "!RCHOICE!"=="1" goto START_DOCKER
call :shutdown_now
pause
exit /b 1

:: ------------------------------------------------------------
:: START - Local
:: ------------------------------------------------------------
:START_LOCAL
call :log "Starting local stack"

if not exist "!REPO_ROOT!\backend\venv\Scripts\python.exe" (
    call :create_venv
    if errorlevel 1 (
        color 0C
        echo          ERROR: venv creation failed. Aborting local start.
        pause
        exit /b 1
    )
)

call :install_backend_deps
if errorlevel 1 (
    color 0C
    echo          ERROR: backend dependency install failed.
    pause
    exit /b 1
)

call :install_frontend_deps
if errorlevel 1 (
    color 0C
    echo          ERROR: frontend dependency install failed.
    pause
    exit /b 1
)

echo          Starting backend window...
start "ULPF Backend" cmd /k "cd /d ""!REPO_ROOT!\backend"" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo          Starting frontend window...
start "ULPF Frontend" cmd /k "cd /d ""!REPO_ROOT!\frontend"" && npm run dev"

call :log "Spawned backend and frontend windows"
call :write_marker
goto WAIT_FOR_READY

:create_venv
echo          Creating Python virtual environment with !PY_LAUNCHER!...
pushd "!REPO_ROOT!\backend"
!PY_LAUNCHER! -m venv venv
set "RC=!ERRORLEVEL!"
popd
if not "!RC!"=="0" goto VENV_FAILED
exit /b 0

:VENV_FAILED
call :log "FATAL: venv creation failed"
exit /b 1

:install_backend_deps
echo          Installing core backend dependencies ^(may take a few minutes^)...
pushd "!REPO_ROOT!\backend"
venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-cache-dir --default-timeout=100 --retries=8 -r requirements.txt >>"%INSTALL_LOG%" 2>&1
set "RC=!ERRORLEVEL!"
if not "!RC!"=="0" (
    call :log "FATAL: pip install failed rc=!RC!"
    popd
    exit /b 1
)
echo          [OK] Core dependencies installed.
echo          Installing optional dependencies ^(may be skipped^)...
venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-cache-dir --default-timeout=100 --retries=8 -r requirements-optional.txt >>"%INSTALL_LOG%" 2>&1
if errorlevel 1 (
    color 0E
    echo          [!!] Optional dependencies failed ^(non-fatal^).
    call :log "WARN: optional dependencies failed"
)
echo          [OK] Optional dependencies step complete.
popd
exit /b 0

:install_frontend_deps
if exist "!REPO_ROOT!\frontend\node_modules" exit /b 0
echo          Installing frontend dependencies ^(may take a few minutes^)...
pushd "!REPO_ROOT!\frontend"
call npm install >>"%INSTALL_LOG%" 2>&1
set "RC=!ERRORLEVEL!"
popd
if not "!RC!"=="0" (
    call :log "FATAL: npm install failed rc=!RC!"
    exit /b 1
)
echo          [OK] Frontend dependencies installed.
exit /b 0

:: ============================================================
:: WAIT FOR READY  (up to 300s for first-run npm install)
:: ============================================================
:WAIT_FOR_READY
color 0B
set /a TICKS=0
set /a MAX_TICKS=150

:WAIT_LOOP
set /a TICKS+=1

if !TICKS! GTR %MAX_TICKS% goto WAIT_TIMEOUT

set "READY=0"
powershell -NoProfile -Command ^
    "try { $r=Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto WAIT_DRAW

powershell -NoProfile -Command ^
    "try { $r=Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto WAIT_DRAW
set "READY=1"

:WAIT_DRAW
set /a PCT=!TICKS!*100/%MAX_TICKS%
if !PCT! GTR 99 set /a PCT=99
set /a FILLED=!PCT!/2
set "BAR="
for /l %%i in (1,1,!FILLED!) do set "BAR=!BAR!#"
set /a SPACES=50-!FILLED!
for /l %%i in (1,1,!SPACES!) do set "BAR=!BAR!."

call :draw_starting

if "!READY!"=="1" goto ENTER_CONTROL_LOOP
timeout /t 2 /nobreak >nul
goto WAIT_LOOP

:WAIT_TIMEOUT
color 0E
cls
call :draw_banner "ULPF DID NOT BECOME READY IN TIME"
echo.
echo     Checked for 300 seconds. Something may be wrong.
echo.
echo     For Docker mode:
echo       docker compose ps
echo       docker compose logs backend
echo.
echo     For local mode, check the "ULPF Backend" window.
echo.
echo     Full log: %INSTALL_LOG%
echo.
pause
call :shutdown_now
exit /b 1

:: ============================================================
:: CONTROL LOOP
:: ============================================================
:ENTER_CONTROL_LOOP
call :log "Services ready. Entering control loop."

call :refresh_connector_state

echo          Opening browser to http://localhost:5173 ...
start "" "http://localhost:5173"

call :check_health
call :draw_console

:CONTROL_TICK
choice /c qslohrbc /n /t 5 /d s /m "ulpf> " >nul 2>&1
set "CE=!ERRORLEVEL!"

if "!CE!"=="1" goto SHUTDOWN_AND_EXIT
if "!CE!"=="2" call :CTL_STATUS
if "!CE!"=="3" call :CTL_LOGS
if "!CE!"=="4" call :CTL_OPEN
if "!CE!"=="5" call :CTL_HELP
if "!CE!"=="6" call :CTL_RESTART
if "!CE!"=="7" call :CTL_REBUILD
if "!CE!"=="8" call :CTL_CLEAR
goto CONTROL_TICK

:CTL_STATUS
call :check_health
call :refresh_connector_state
call :draw_console
goto CONTROL_TICK

:CTL_LOGS
call :show_logs
goto CONTROL_TICK

:CTL_OPEN
start "" "http://localhost:5173"
goto CONTROL_TICK

:CTL_HELP
call :draw_help
pause >nul
call :draw_console
goto CONTROL_TICK

:CTL_RESTART
call :restart_stack
call :check_health
call :refresh_connector_state
call :draw_console
goto CONTROL_TICK

:CTL_REBUILD
call :force_rebuild
call :check_health
call :refresh_connector_state
call :draw_console
goto CONTROL_TICK

:CTL_CLEAR
cls
call :draw_console
goto CONTROL_TICK

:: ============================================================
:: SHUTDOWN
:: ============================================================
:SHUTDOWN_AND_EXIT
color 0E
cls
call :draw_banner "SHUTTING DOWN"
echo.
echo     Stopping services...
echo.
call :shutdown_now
color 0A
echo.
call :draw_banner "ULPF HAS BEEN STOPPED"
echo.
echo     Thanks for using ULPF.
echo.
call :log "Clean shutdown complete."
echo     This window will close in 3 seconds.
timeout /t 3 /nobreak >nul

exit

:shutdown_now
if not "!MODE!"=="docker" goto SHUTDOWN_LOCAL
docker compose down
if errorlevel 1 goto SHUTDOWN_DOCKER_ERR
echo     [OK] Docker stack stopped.
exit /b 0

:SHUTDOWN_DOCKER_ERR
echo     [!] docker compose down reported an error.
exit /b 0

:SHUTDOWN_LOCAL
taskkill /FI "WINDOWTITLE eq ULPF Backend*" /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq ULPF Frontend*" /T >nul 2>&1
timeout /t 2 /nobreak >nul
taskkill /FI "WINDOWTITLE eq ULPF Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ULPF Frontend*" /T /F >nul 2>&1
echo     [OK] Local windows closed.
exit /b 0

:: ============================================================
:: SUBROUTINES
:: ============================================================

:parse_arg
if /i "%~1"=="--reset-env"    set "ARG_RESET_ENV=1"
if /i "%~1"=="--rebuild"      set "ARG_REBUILD=1"
if /i "%~1"=="--no-connector" set "ARG_NO_CONNECTOR=1"
if /i "%~1"=="--no-auto"      set "ARG_AUTO=0"
if /i "%~1"=="--docker"       set "ARG_MODE=1"
if /i "%~1"=="--local"        set "ARG_MODE=2"
exit /b 0

:log
echo [%DATE% %TIME%] %~1>>"%INSTALL_LOG%"
exit /b 0

:: ------------------------------------------------------------
:: Prerequisite checks
:: ------------------------------------------------------------
:check_docker
docker --version >nul 2>&1
if errorlevel 1 goto CHECK_DOCKER_MISSING
for /f "tokens=*" %%v in ('docker --version 2^>nul') do set "DOCKER_VER=%%v"
echo          [OK] !DOCKER_VER!
call :log "Docker detected: !DOCKER_VER!"
set "DOCKER_OK=1"
exit /b 0

:CHECK_DOCKER_MISSING
echo          [--] Docker not found.
call :log "Docker not found"
exit /b 0

:: ------------------------------------------------------------
:: Python detection
::
:: ULPF supports Python 3.10, 3.11, and 3.12 only.
:: If multiple versions are installed, the newest supported one
:: is picked automatically. Lookup order:
::   1. py launcher: py -3.12, then py -3.11, then py -3.10
::   2. bare "python" on PATH, but only if it's 3.10/3.11/3.12
::   3. bare "python3" on PATH, same constraint
::
:: The chosen launcher is stored in PY_LAUNCHER and reused
:: everywhere a Python command is run.
:: ------------------------------------------------------------
:check_python
set "PY_LAUNCHER="
set "PY_VER="

:: 1. Try the py launcher for each supported version, newest first
for %%V in (3.12 3.11 3.10) do (
    if "!PY_LAUNCHER!"=="" (
        py -%%V --version >nul 2>&1
        if not errorlevel 1 call :probe_py "py -%%V"
    )
)

:: 2. Try "python" on PATH
if "!PY_LAUNCHER!"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 call :probe_py "python"
)

:: 3. Try "python3" on PATH
if "!PY_LAUNCHER!"=="" (
    python3 --version >nul 2>&1
    if not errorlevel 1 call :probe_py "python3"
)

if "!PY_LAUNCHER!"=="" goto CHECK_PY_MISSING
echo          [OK] !PY_VER!  ^(launcher: !PY_LAUNCHER!^)
call :log "Python detected: !PY_VER! via !PY_LAUNCHER!"
exit /b 0

:: ------------------------------------------------------------
:: Probe a candidate launcher. Sets PY_LAUNCHER and PY_VER if
:: the reported version is 3.10, 3.11, or 3.12. No-op otherwise.
:: ------------------------------------------------------------
:probe_py
set "CANDIDATE=%~1"
set "VER_RAW="
for /f "tokens=*" %%v in ('%CANDIDATE% --version 2^>nul') do set "VER_RAW=%%v"
if "!VER_RAW!"=="" exit /b 0

:: Extract "3.X" from "Python 3.X.Y"
set "VER_NUM=!VER_RAW:Python =!"
for /f "tokens=1,2 delims=." %%a in ("!VER_NUM!") do (
    set "CAND_MAJOR=%%a"
    set "CAND_MINOR=%%b"
)

:: Strip trailing non-numeric junk (some launchers append tags)
for /f "tokens=1 delims= " %%m in ("!CAND_MINOR!") do set "CAND_MINOR=%%m"

if not "!CAND_MAJOR!"=="3" exit /b 0
if "!CAND_MINOR!"=="10" goto PROBE_PY_ACCEPT
if "!CAND_MINOR!"=="11" goto PROBE_PY_ACCEPT
if "!CAND_MINOR!"=="12" goto PROBE_PY_ACCEPT
exit /b 0

:PROBE_PY_ACCEPT
set "PY_LAUNCHER=!CANDIDATE!"
set "PY_VER=!VER_RAW!"
exit /b 0

:CHECK_PY_MISSING
echo          [--] Python 3.10 / 3.11 / 3.12 not found.
call :log "Python not found (3.10-3.12 required)"
exit /b 0

:check_node
node --version >nul 2>&1
if errorlevel 1 goto CHECK_NODE_MISSING
for /f "tokens=*" %%v in ('node --version 2^>nul') do set "NODE_VER=%%v"
set "NODE_NUM=!NODE_VER:v=!"
for /f "tokens=1 delims=." %%v in ("!NODE_NUM!") do set "NODE_MAJOR=%%v"
if !NODE_MAJOR! LSS 18 goto CHECK_NODE_OLD
echo          [OK] Node !NODE_VER!
call :log "Node detected: !NODE_VER!"
exit /b 0

:CHECK_NODE_OLD
echo          [!!] Node !NODE_VER! ^(need 18+^)
call :log "Node too old: !NODE_VER!"
set "NODE_VER="
exit /b 0

:CHECK_NODE_MISSING
echo          [--] Node not found.
call :log "Node not found"
exit /b 0

:: ------------------------------------------------------------
:: Connector service
:: ------------------------------------------------------------
:setup_connector_service
set "CONNECTOR_DIR=!REPO_ROOT!\scripts\ulpf-connector"

if not exist "!CONNECTOR_DATA_DIR!" mkdir "!CONNECTOR_DATA_DIR!" >nul 2>&1
icacls "!CONNECTOR_DATA_DIR!" /grant "SYSTEM:(OI)(CI)F" /grant "Administrators:(OI)(CI)F" /T >nul 2>&1

if exist "%ULPF_HOME%\connector.json" if not exist "!CONNECTOR_CONFIG!" (
    copy /Y "%ULPF_HOME%\connector.json" "!CONNECTOR_CONFIG!" >nul
    echo          [OK] Migrated connector config to !CONNECTOR_DATA_DIR!
)

if not exist "!CONNECTOR_CONFIG!" call :seed_connector_config
if exist "!CONNECTOR_DIR!\fix_config.py" call :fix_connector_config

call :query_connector_status
echo          Current status: !SVC_LINE!
call :log "Connector status: rc=!SVC_RC! line=!SVC_LINE!"

if "!SVC_RC!"=="0" if "!SVC_LINE!"=="connector.service.status=installed,running" goto CONNECTOR_ALREADY
goto CONNECTOR_INSTALL

:seed_connector_config
if not exist "!CONNECTOR_DIR!\config.example.json" goto SEED_NO_TEMPLATE
copy /Y "!CONNECTOR_DIR!\config.example.json" "!CONNECTOR_CONFIG!" >nul
echo          [OK] Created !CONNECTOR_CONFIG! from template.
exit /b 0

:SEED_NO_TEMPLATE
(
    echo {
    echo   "ulpf_base": "http://localhost:8000",
    echo   "log_level": "INFO",
    echo   "log_file": "C:\\ProgramData\\ULPF\\connector.log",
    echo   "auth": {
    echo     "email": "admin@ulpf.local",
    echo     "password": "ChangeMe_Admin123!",
    echo     "password_env": "ULPF_CONNECTOR_PASSWORD"
    echo   },
    echo   "queue": {
    echo     "max_in_memory": 1000,
    echo     "spool_file": "C:\\ProgramData\\ULPF\\spool.jsonl",
    echo     "spool_replay_on_start": true
    echo   },
    echo   "http": {
    echo     "timeout_s": 30.0,
    echo     "max_retries": 5,
    echo     "backoff_base_s": 0.5,
    echo     "backoff_max_s": 30.0
    echo   },
    echo   "adapters": {
    echo     "windows_eventlog": {
    echo       "enabled": "auto",
    echo       "channels": ["Security", "System", "Application"],
    echo       "filter_xpath": "*",
    echo       "poll_seconds": 2.0,
    echo       "max_events_per_poll": 200,
    echo       "bookmark_file": "C:\\ProgramData\\ULPF\\win_eventlog.bookmark.json",
    echo       "resume_from_bookmark": false
    echo     }
    echo   }
    echo }
) >"!CONNECTOR_CONFIG!"
echo          [OK] Wrote default connector config.
exit /b 0

:fix_connector_config
!PY_LAUNCHER! "!CONNECTOR_DIR!\fix_config.py" --path "!CONNECTOR_CONFIG!" >>"%INSTALL_LOG%" 2>&1
echo          [OK] Connector config normalized.
exit /b 0

:query_connector_status
set "SVC_LINE="
!PY_LAUNCHER! "!CONNECTOR_DIR!\install_service.py" --status --config "!CONNECTOR_CONFIG!" >"%TEMP%\ulpf_svc.txt" 2>&1
set "SVC_RC=!ERRORLEVEL!"
for /f "usebackq tokens=*" %%L in ("%TEMP%\ulpf_svc.txt") do set "SVC_LINE=%%L"
del "%TEMP%\ulpf_svc.txt" >nul 2>&1
exit /b 0

:refresh_connector_state
if "!PY_LAUNCHER!"=="" goto REFRESH_CONNECTOR_NO_PY
if not exist "!REPO_ROOT!\scripts\ulpf-connector\install_service.py" goto REFRESH_CONNECTOR_NO_SCRIPTS
set "CONNECTOR_DIR=!REPO_ROOT!\scripts\ulpf-connector"
if not exist "!CONNECTOR_CONFIG!" goto REFRESH_CONNECTOR_NO_CONFIG

:: Only re-poll every 30s
for /f "tokens=*" %%T in ('powershell -NoProfile -Command "[int][double]::Parse((Get-Date -UFormat %%s))"') do set "NOW_TS=%%T"
set /a SINCE=!NOW_TS!-!SVC_CACHE_TS!
if !SINCE! LSS 30 if not "!CONNECTOR_STATE!"=="unknown" exit /b 0

set "SVC_LINE="
!PY_LAUNCHER! "!CONNECTOR_DIR!\install_service.py" --status --config "!CONNECTOR_CONFIG!" >"%TEMP%\ulpf_svc2.txt" 2>&1
set "SVC_RC=!ERRORLEVEL!"
for /f "usebackq tokens=*" %%L in ("%TEMP%\ulpf_svc2.txt") do set "SVC_LINE=%%L"
del "%TEMP%\ulpf_svc2.txt" >nul 2>&1
set "SVC_CACHE_TS=!NOW_TS!"

if "!SVC_RC!"=="0" if "!SVC_LINE!"=="connector.service.status=installed,running" goto REFRESH_CONNECTOR_RUNNING
if "!SVC_LINE!"=="connector.service.status=installed,stopped" goto REFRESH_CONNECTOR_STOPPED
if "!SVC_LINE!"=="connector.service.status=not_installed" goto REFRESH_CONNECTOR_MISSING
set "CONNECTOR_STATE=unknown"
exit /b 0

:REFRESH_CONNECTOR_RUNNING
set "CONNECTOR_STATE=OK running"
exit /b 0

:REFRESH_CONNECTOR_STOPPED
set "CONNECTOR_STATE=!! installed but stopped"
exit /b 0

:REFRESH_CONNECTOR_MISSING
set "CONNECTOR_STATE=-- not installed"
exit /b 0

:REFRESH_CONNECTOR_NO_PY
set "CONNECTOR_STATE=-- no supported host Python"
exit /b 0

:REFRESH_CONNECTOR_NO_SCRIPTS
set "CONNECTOR_STATE=-- scripts missing"
exit /b 0

:REFRESH_CONNECTOR_NO_CONFIG
set "CONNECTOR_STATE=-- no config"
exit /b 0

:CONNECTOR_ALREADY
echo          [OK] Connector service is already running.
exit /b 0

:CONNECTOR_INSTALL
echo          Installing / starting connector service...
!PY_LAUNCHER! "!CONNECTOR_DIR!\install_service.py" --config "!CONNECTOR_CONFIG!" >>"%INSTALL_LOG%" 2>&1
set "INST_RC=!ERRORLEVEL!"
call :log "Connector install rc=!INST_RC!"
if "!INST_RC!"=="0" goto CONNECTOR_INSTALL_VERIFY

echo          [!!] First attempt failed ^(rc=!INST_RC!^). Retrying once...
call :log "Connector install failed rc=!INST_RC! - retrying once"
timeout /t 2 /nobreak >nul
!PY_LAUNCHER! "!CONNECTOR_DIR!\install_service.py" --config "!CONNECTOR_CONFIG!" >>"%INSTALL_LOG%" 2>&1
set "INST_RC=!ERRORLEVEL!"
call :log "Connector install (retry) rc=!INST_RC!"
if "!INST_RC!"=="0" goto CONNECTOR_INSTALL_VERIFY

color 0E
echo          [!!] Connector install failed ^(rc=!INST_RC!^). See %INSTALL_LOG%.
echo               ULPF will still start, but host log streaming is off.
color 0B
exit /b 0

:CONNECTOR_INSTALL_VERIFY
set /a VWAIT=0
:CONNECTOR_VERIFY_LOOP
timeout /t 2 /nobreak >nul
set /a VWAIT+=2
call :query_connector_status
if "!SVC_LINE!"=="connector.service.status=installed,running" goto CONNECTOR_INSTALL_OK
if !VWAIT! LSS 15 goto CONNECTOR_VERIFY_LOOP

color 0E
echo          [!!] Task installed but the process did not report running after !VWAIT!s.
echo               Re-run manually to see the error:
echo                 !PY_LAUNCHER! "!CONNECTOR_DIR!\connector.py" --config "!CONNECTOR_CONFIG!"
call :log "Connector task not running after !VWAIT!s: !SVC_LINE!"
color 0B
exit /b 0

:CONNECTOR_INSTALL_OK
echo          [OK] Connector service installed and running.
exit /b 0

:: ------------------------------------------------------------
:: .env helpers
:: ------------------------------------------------------------
:patch_env_for_docker
powershell -NoProfile -Command ^
    "$p='!REPO_ROOT!\.env'; $c=Get-Content -Raw -LiteralPath $p; " ^
    "$c=$c -replace 'DATABASE_URL=postgresql\+psycopg://ulpf:ulpf@localhost:5432/ulpf','DATABASE_URL=postgresql+psycopg://ulpf:ulpf@postgres:5432/ulpf'; " ^
    "$c=$c -replace 'REDIS_URL=redis://localhost:6379/0','REDIS_URL=redis://redis:6379/0'; " ^
    "$c=$c -replace 'MINIO_ENDPOINT=localhost:9000','MINIO_ENDPOINT=minio:9000'; " ^
    "Set-Content -LiteralPath $p -Value $c -NoNewline -Encoding UTF8"
if errorlevel 1 goto PATCH_ENV_WARN
echo          [OK] .env patched for Docker networking.
call :log "Docker .env patched"
exit /b 0

:PATCH_ENV_WARN
color 0E
echo          [!!] Failed to patch .env for Docker. Continuing.
call :log "WARN: .env patch failed"
exit /b 0

:rotate_env_backups
powershell -NoProfile -Command ^
    "Get-ChildItem -LiteralPath '!REPO_ROOT!' -Filter '.env.bak.*' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Force -ErrorAction SilentlyContinue"
exit /b 0

:: ------------------------------------------------------------
:: Marker file
:: ------------------------------------------------------------
:write_marker
set "REQ_SHA="
set "COMPOSE_SHA="
set "DOCKERFILE_SHA="
if not "!MODE!"=="docker" goto WRITE_MARKER_WRITE
for /f "usebackq tokens=*" %%H in (`powershell -NoProfile -Command "if (Test-Path '!REPO_ROOT!\backend\requirements.txt') { (Get-FileHash -Algorithm SHA256 '!REPO_ROOT!\backend\requirements.txt').Hash }"`) do set "REQ_SHA=%%H"
for /f "usebackq tokens=*" %%H in (`powershell -NoProfile -Command "if (Test-Path '!REPO_ROOT!\docker-compose.yml') { (Get-FileHash -Algorithm SHA256 '!REPO_ROOT!\docker-compose.yml').Hash }"`) do set "COMPOSE_SHA=%%H"
for /f "usebackq tokens=*" %%H in (`powershell -NoProfile -Command "if (Test-Path '!REPO_ROOT!\backend\Dockerfile') { (Get-FileHash -Algorithm SHA256 '!REPO_ROOT!\backend\Dockerfile').Hash }"`) do set "DOCKERFILE_SHA=%%H"

:WRITE_MARKER_WRITE
(
    echo {
    echo   "first_run": "!FIRST_RUN!",
    echo   "last_run": "%DATE% %TIME%",
    echo   "mode": "!MODE!",
    echo   "repo_root": "!REPO_ROOT!",
    echo   "docker_available": "!DOCKER_OK!",
    echo   "python_version": "!PY_VER!",
    echo   "python_launcher": "!PY_LAUNCHER!",
    echo   "node_version": "!NODE_VER!",
    echo   "requirements_sha": "!REQ_SHA!",
    echo   "compose_sha": "!COMPOSE_SHA!",
    echo   "dockerfile_sha": "!DOCKERFILE_SHA!"
    echo }
) >"%INSTALL_MARKER%"
exit /b 0

:: ------------------------------------------------------------
:: Rebuild decision
:: ------------------------------------------------------------
:detect_stale_build
if not exist "%INSTALL_MARKER%" goto DETECT_STALE_MARKER_MISSING
set "OLD_REQ="
for /f "usebackq tokens=2 delims=:," %%v in (`powershell -NoProfile -Command "try { (Get-Content -Raw '%INSTALL_MARKER%' | ConvertFrom-Json).requirements_sha } catch { '' }"`) do set "OLD_REQ=%%v"
set "OLD_REQ=!OLD_REQ: =!"
set "OLD_REQ=!OLD_REQ:"=!"
set "CUR_REQ="
for /f "usebackq tokens=*" %%H in (`powershell -NoProfile -Command "if (Test-Path '!REPO_ROOT!\backend\requirements.txt') { (Get-FileHash -Algorithm SHA256 '!REPO_ROOT!\backend\requirements.txt').Hash }"`) do set "CUR_REQ=%%H"
if "!OLD_REQ!"=="!CUR_REQ!" exit /b 0
goto DETECT_STALE_PROMPT

:DETECT_STALE_MARKER_MISSING
docker image inspect sih-main-backend >nul 2>&1
if errorlevel 1 (
    call :log "No marker and no backend image; letting 'up -d' build it"
    exit /b 0
)
set "NEED_REBUILD=1"
call :log "No marker but backend image exists; will rebuild"
exit /b 0

:DETECT_STALE_PROMPT
if "!ARG_AUTO!"=="1" goto DETECT_STALE_AUTO
echo.
echo   ------------------------------------------------------------
echo     requirements.txt changed since last run.
echo     A rebuild is recommended to install the new dependencies.
echo   ------------------------------------------------------------
echo.
set /p "RBCHOICE=          Rebuild now? [y/N]: "
if /i not "!RBCHOICE!"=="y" goto DETECT_STALE_DECLINE
set "NEED_REBUILD=1"
call :log "User accepted rebuild (req hash mismatch)"
exit /b 0

:DETECT_STALE_AUTO
set "NEED_REBUILD=1"
call :log "Auto-rebuild (req hash mismatch, --auto)"
exit /b 0

:DETECT_STALE_DECLINE
call :log "User declined rebuild (req hash mismatch)"
exit /b 0

:docker_rebuild
echo          Rebuilding images ^(--no-cache, this may take a few minutes^)...
echo.
docker compose build --no-cache backend frontend
set "RB_EXIT=!ERRORLEVEL!"
call :log "docker compose build exit code: !RB_EXIT!"
if "!RB_EXIT!"=="0" goto DOCKER_REBUILD_OK
color 0E
echo          [!!] Build failed. See output above.
echo.
pause
call :shutdown_now
exit /b 1

:DOCKER_REBUILD_OK
echo          [OK] Images rebuilt.
exit /b 0

:: ------------------------------------------------------------
:: Force rebuild (mode-aware)
:: ------------------------------------------------------------
:force_rebuild
color 0E
cls
call :draw_banner "REBUILD"
echo.
if "!MODE!"=="docker" goto FORCE_REBUILD_DOCKER
if "!MODE!"=="local"  goto FORCE_REBUILD_LOCAL
exit /b 0

:FORCE_REBUILD_DOCKER
echo     This will run:
echo       docker compose build --no-cache backend frontend
echo       docker compose up -d --remove-orphans
echo.
echo     Expect 3-6 minutes. Your data in Postgres/MinIO is preserved.
echo.
set /p "RBOK=          Proceed? [y/N]: "
if /i not "!RBOK!"=="y" goto FORCE_REBUILD_CANCEL

echo.
echo     Building...
docker compose build --no-cache backend frontend
if errorlevel 1 goto FORCE_REBUILD_FAIL
echo.
echo     Recreating containers...
docker compose up -d --remove-orphans
if errorlevel 1 goto FORCE_REBUILD_FAIL
echo.
echo     [OK] Rebuild complete.
call :write_marker
color 0B
timeout /t 2 /nobreak >nul
exit /b 0

:FORCE_REBUILD_LOCAL
echo     This will reinstall dependencies and restart local windows:
echo       - pip install -r backend\requirements.txt
echo       - npm install ^(if node_modules missing^)
echo       - restart "ULPF Backend" and "ULPF Frontend" windows
echo.
set /p "RBOK=          Proceed? [y/N]: "
if /i not "!RBOK!"=="y" goto FORCE_REBUILD_CANCEL

echo.
echo     Restarting local services...
call :restart_stack
echo.
echo     [OK] Local rebuild complete.
call :write_marker
color 0B
timeout /t 2 /nobreak >nul
exit /b 0

:FORCE_REBUILD_CANCEL
exit /b 0

:FORCE_REBUILD_FAIL
color 0C
echo.
echo     [!!] Rebuild failed. See output above.
pause
color 0B
exit /b 1

:: ------------------------------------------------------------
:: Drawing helpers
:: ------------------------------------------------------------
:draw_header
cls
echo.
echo   ============================================================
echo.
echo               U L P F   -   S E T U P
echo.
echo        Universal Log Pre-Processing Framework
echo.
echo   ============================================================
exit /b 0

:draw_mode_menu
cls
echo.
echo   ============================================================
echo.
echo               U L P F   -   S E T U P
echo.
echo        Universal Log Pre-Processing Framework
echo.
echo   ============================================================
echo.
echo        How would you like to run ULPF?
echo.
echo   ------------------------------------------------------------
echo        [1]  Docker      ^(recommended — no local installs^)
echo        [2]  Local       ^(uses existing Python + Node^)
echo        [3]  Exit
echo   ------------------------------------------------------------
echo.
exit /b 0

:draw_banner
echo   ============================================================
echo     %~1
echo   ============================================================
exit /b 0

:draw_step
echo.
echo   [%~1/4]  %~2...
exit /b 0

:draw_starting
cls
echo.
echo   ============================================================
echo.
echo     ULPF is starting...
echo.
echo   ============================================================
echo.
echo     Mode:     !MODE!
echo     Progress: [!BAR!] !PCT!%%
echo.
echo     Waiting for frontend and backend...
echo.
echo     This may take 30-90 seconds on first run
echo     ^(containers are being built and images downloaded^).
echo.
exit /b 0

:check_health
powershell -NoProfile -Command ^
    "try { $r=Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto CHECK_HEALTH_DOWN
set "LAST_CHECK=ok"
exit /b 0

:CHECK_HEALTH_DOWN
set "LAST_CHECK=DOWN"
exit /b 0

:draw_console
cls
echo.
echo   ============================================================
echo.
echo                U L P F   I S   R U N N I N G
echo.
echo   ============================================================
echo.
echo     Mode:      !MODE!
echo     Frontend:  http://localhost:5173
echo     API:       http://localhost:8000
echo     API Docs:  http://localhost:8000/docs
echo.
echo   ------------------------------------------------------------
if "!LAST_CHECK!"=="ok" goto CONSOLE_OK
echo     Backend:   [!!] DOWN ^(last health check failed^)
goto CONSOLE_CONNECTOR

:CONSOLE_OK
echo     Backend:   [OK] healthy

:CONSOLE_CONNECTOR
if "!CONNECTOR_STATE!"=="OK running" goto CONSOLE_CONNECTOR_OK
echo     Connector: !CONNECTOR_STATE!
goto CONSOLE_COMMANDS

:CONSOLE_CONNECTOR_OK
echo     Connector: [OK] running

:CONSOLE_COMMANDS
echo   ------------------------------------------------------------
echo     Commands
echo   ------------------------------------------------------------
echo.
echo       [s]  Status    - re-check backend + connector health
echo       [l]  Logs      - show recent backend logs
echo       [o]  Open      - open ULPF in browser
echo       [h]  Help      - show this list
echo       [r]  Restart   - restart the stack
echo       [b]  Rebuild   - rebuild images ^(after code/dep changes^)
echo       [c]  Clear     - redraw this console
echo       [q]  Quit      - stop ULPF and close this window
echo.
echo   ------------------------------------------------------------
echo     First-time login:  admin@ulpf.local / ChangeMe_Admin123!
echo   ------------------------------------------------------------
echo.
exit /b 0

:draw_help
cls
echo.
call :draw_banner "ULPF CONTROL - HELP"
echo.
echo     The console polls health every 5 seconds and refreshes
echo     automatically. You can type a key at any time:
echo.
echo       s   Force a health check right now ^(backend + connector^).
echo       l   Show the last 30 lines of backend logs.
echo       o   Open http://localhost:5173 in your browser.
echo       h   Show this help.
echo       r   Restart the stack.
echo       b   Rebuild from scratch. Docker: docker compose build.
echo           Local: pip install + npm install + restart windows.
echo       c   Clear and redraw the console.
echo       q   Stop everything and close this window.
echo.
echo     The host log connector runs as a Windows scheduled task,
echo     a systemd unit, or a launchd agent. It starts at boot and
echo     streams events to ULPF independently of this console.
echo.
echo     If Connector shows "not installed" or "stopped", run this
echo     script once as Administrator (right-click the .bat file
echo     and choose "Run as administrator") to install it.
echo.
echo     Press any key to return to the console.
exit /b 0

:show_logs
cls
echo.
call :draw_banner "RECENT BACKEND LOGS"
echo.
if not "!MODE!"=="docker" goto SHOW_LOGS_LOCAL
docker compose logs --tail=30 backend 2>&1
goto SHOW_LOGS_DONE

:SHOW_LOGS_LOCAL
echo     Local mode: see the "ULPF Backend" window for logs.

:SHOW_LOGS_DONE
echo.
echo     Press any key to return to the console.
pause >nul
call :draw_console
exit /b 0

:restart_stack
color 0E
cls
call :draw_banner "RESTARTING"
echo.
if not "!MODE!"=="docker" goto RESTART_LOCAL

echo     Restarting Docker stack...
docker compose restart
if errorlevel 1 goto RESTART_DOCKER_ERR
echo     [OK] Stack restarted.
goto RESTART_DONE

:RESTART_DOCKER_ERR
echo     [!] Restart reported an error.
goto RESTART_DONE

:RESTART_LOCAL
echo     Closing local windows...
taskkill /FI "WINDOWTITLE eq ULPF Backend*" /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq ULPF Frontend*" /T >nul 2>&1
timeout /t 2 /nobreak >nul
taskkill /FI "WINDOWTITLE eq ULPF Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ULPF Frontend*" /T /F >nul 2>&1
timeout /t 1 /nobreak >nul
echo     Respawning...
start "ULPF Backend" cmd /k "cd /d ""!REPO_ROOT!\backend"" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "ULPF Frontend" cmd /k "cd /d ""!REPO_ROOT!\frontend"" && npm run dev"
echo     [OK] Local windows restarted.

:RESTART_DONE
color 0B
timeout /t 2 /nobreak >nul
exit /b 0