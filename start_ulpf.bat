@echo off
setlocal EnableDelayedExpansion EnableExtensions
title ULPF Control
color 0B
chcp 65001 >nul 2>&1

:: ============================================================
::  ULPF - Entry Point
::
::  This file:
::    1. Requests Administrator
::    2. Asks Docker or Local
::    3. Installs the host log connector service
::    4. Hands off to scripts\run_docker.bat OR scripts\run_local.bat
::
::  All heavy lifting lives in the scripts\ worker bats.
:: ============================================================

:: -------------------- Elevation --------------------
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
echo     Administrator privileges are needed to install and
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

:: -------------------- Repo root + state --------------------
set "REPO_ROOT=%~dp0"
if "!REPO_ROOT:~-1!"=="\" set "REPO_ROOT=!REPO_ROOT:~0,-1!"
cd /d "!REPO_ROOT!"

set "ULPF_HOME=%USERPROFILE%\.ulpf"
if not exist "%ULPF_HOME%" mkdir "%ULPF_HOME%" >nul 2>&1
set "INSTALL_LOG=%ULPF_HOME%\install.log"

set "CONNECTOR_DATA_DIR=C:\ProgramData\ULPF"
set "CONNECTOR_CONFIG=!CONNECTOR_DATA_DIR!\connector.json"

set "MODE="
set "PY_LAUNCHER="
set "PY_VER="

:: -------------------- Header --------------------
call :draw_header
echo.
echo       This will prepare and start ULPF on your computer.
echo.
call :log "===== ULPF setup starting ====="
call :log "Repo root: !REPO_ROOT!"

:: ============================================================
:: STEP 1 - MODE SELECTION
:: ============================================================
:: Support direct CLI arguments (e.g. start_ulpf.bat docker)
if /i "%~1"=="1" goto MODE_DOCKER
if /i "%~1"=="docker" goto MODE_DOCKER
if /i "%~1"=="--docker" goto MODE_DOCKER
if /i "%~1"=="2" goto MODE_LOCAL
if /i "%~1"=="local" goto MODE_LOCAL
if /i "%~1"=="--local" goto MODE_LOCAL

call :draw_mode_menu
echo        Starting in Docker mode automatically in 5 seconds...
echo        Press 1 for Docker, 2 for Local, or 3 to Exit.
echo.
choice /c 123 /t 5 /d 1 /m "          Enter choice"
set "CHOICE=!ERRORLEVEL!"

if "!CHOICE!"=="1" goto MODE_DOCKER
if "!CHOICE!"=="2" goto MODE_LOCAL
if "!CHOICE!"=="3" goto MODE_EXIT

:MODE_EXIT
echo.
echo          Exiting.
exit /b 0

:MODE_DOCKER
set "MODE=docker"
call :log "Mode: docker"
call :check_docker
if "!DOCKER_OK!"=="1" goto MODE_READY
color 0E
echo.
echo          [!!] Docker is not available.
echo.
echo            [1]  Open Docker Desktop download page
echo            [2]  Exit
echo.
set /p "DRCHOICE=          Enter choice [1/2]: "
if "!DRCHOICE!"=="1" start "" "https://www.docker.com/products/docker-desktop/"
exit /b 0

:MODE_LOCAL
set "MODE=local"
call :log "Mode: local"
call :check_python
if "!PY_LAUNCHER!"=="" goto MODE_LOCAL_NO_PY
echo          [OK] !PY_VER!  ^(launcher: !PY_LAUNCHER!^)
goto MODE_READY

:MODE_LOCAL_NO_PY
color 0C
echo.
echo          [!!] Local mode requires Python 3.10, 3.11, or 3.12.
echo.
echo               Installed versions detected by py launcher:
py -0p 2>nul
echo.
echo               Install Python 3.12 from python.org and check
echo               "Add Python to PATH" during install.
echo.
pause
exit /b 0

:MODE_READY
call :log "Mode locked: !MODE!"

:: Ensure root .env exists
if not exist "!REPO_ROOT!\.env" (
    if exist "!REPO_ROOT!\.env.example" (
        copy /Y "!REPO_ROOT!\.env.example" "!REPO_ROOT!\.env" >nul
        echo          [OK] Created initial .env configuration.
    )
)

:: ============================================================
:: STEP 2 - CONNECTOR SERVICE (common to both modes)
:: ============================================================
call :draw_step 1 "Host log connector"
echo.

if "!PY_LAUNCHER!"=="" call :check_python
if "!PY_LAUNCHER!"=="" goto CONNECTOR_SKIP_NO_PY
if not exist "!REPO_ROOT!\scripts\ulpf-connector\connector.py" goto CONNECTOR_SKIP_NO_SCRIPTS

call :setup_connector_service
goto STEP_DISPATCH

:CONNECTOR_SKIP_NO_PY
color 0E
echo          [--] Connector skipped: no supported host Python.
goto STEP_DISPATCH

:CONNECTOR_SKIP_NO_SCRIPTS
color 0E
echo          [--] Connector skipped: scripts not found.
goto STEP_DISPATCH

:: ============================================================
:: STEP 3 - DISPATCH TO WORKER
:: ============================================================
:STEP_DISPATCH
echo.
call :draw_step 2 "Handing off to !MODE! worker"
echo.

if "!MODE!"=="docker" goto DISPATCH_DOCKER
if "!MODE!"=="local"  goto DISPATCH_LOCAL

:DISPATCH_DOCKER
if not exist "!REPO_ROOT!\scripts\run_docker.bat" (
    color 0C
    echo          ERROR: scripts\run_docker.bat not found.
    pause
    exit /b 1
)
call :log "Dispatching to run_docker.bat"
call "!REPO_ROOT!\scripts\run_docker.bat"
exit /b 0

:DISPATCH_LOCAL
if not exist "!REPO_ROOT!\scripts\run_local.bat" (
    color 0C
    echo          ERROR: scripts\run_local.bat not found.
    pause
    exit /b 1
)
call :log "Dispatching to run_local.bat"
call "!REPO_ROOT!\scripts\run_local.bat"
exit /b 0

:: ============================================================
:: HELPERS
:: ============================================================

:log
echo [%DATE% %TIME%] %~1>>"%INSTALL_LOG%"
exit /b 0

:check_docker
set "DOCKER_OK=0"
docker --version >nul 2>&1
if errorlevel 1 exit /b 0
for /f "tokens=*" %%v in ('docker --version 2^>nul') do set "DOCKER_VER=%%v"
echo          [OK] !DOCKER_VER!
set "DOCKER_OK=1"
exit /b 0

:check_python
set "PY_LAUNCHER="
set "PY_VER="

call :try_python "py -3.12"
if not "!PY_LAUNCHER!"=="" exit /b 0
call :try_python "py -3.11"
if not "!PY_LAUNCHER!"=="" exit /b 0
call :try_python "py -3.10"
if not "!PY_LAUNCHER!"=="" exit /b 0
call :try_python "python"
if not "!PY_LAUNCHER!"=="" exit /b 0
call :try_python "python3"
exit /b 0

:try_python
set "CANDIDATE=%~1"
set "RAW="
for /f "usebackq tokens=*" %%v in (`%CANDIDATE% --version 2^>^&1`) do set "RAW=%%v"
if "!RAW!"=="" exit /b 0
set "P10=!RAW:~0,11!"
if "!P10!"=="Python 3.10" goto TRY_PY_ACCEPT
set "P11=!RAW:~0,11!"
if "!P11!"=="Python 3.11" goto TRY_PY_ACCEPT
set "P12=!RAW:~0,11!"
if "!P12!"=="Python 3.12" goto TRY_PY_ACCEPT
exit /b 0

:TRY_PY_ACCEPT
set "PY_LAUNCHER=!CANDIDATE!"
set "PY_VER=!RAW!"
exit /b 0

:setup_connector_service
set "CONNECTOR_DIR=!REPO_ROOT!\scripts\ulpf-connector"

if not exist "!CONNECTOR_DATA_DIR!" mkdir "!CONNECTOR_DATA_DIR!" >nul 2>&1
icacls "!CONNECTOR_DATA_DIR!" /grant "SYSTEM:(OI)(CI)F" /grant "Administrators:(OI)(CI)F" /grant "Users:(OI)(CI)M" /grant "Everyone:(OI)(CI)M" /T >nul 2>&1

if exist "%ULPF_HOME%\connector.json" if not exist "!CONNECTOR_CONFIG!" (
    copy /Y "%ULPF_HOME%\connector.json" "!CONNECTOR_CONFIG!" >nul
    echo          [OK] Migrated connector config.
)

if not exist "!CONNECTOR_CONFIG!" call :seed_connector_config
if exist "!CONNECTOR_DIR!\fix_config.py" call :fix_connector_config

:: Ensure connector dependencies are installed
if exist "!CONNECTOR_DIR!\requirements.txt" (
    !PY_LAUNCHER! -m pip install --quiet -r "!CONNECTOR_DIR!\requirements.txt" >>"%INSTALL_LOG%" 2>&1
)

call :query_connector_status
echo          Current status: !SVC_LINE!
call :log "Connector status: rc=!SVC_RC! line=!SVC_LINE!"

if "!SVC_RC!"=="0" if "!SVC_LINE!"=="connector.service.status=installed,running" goto CONNECTOR_ALREADY
goto CONNECTOR_INSTALL

:seed_connector_config
if not exist "!CONNECTOR_DIR!\config.example.json" goto SEED_DEFAULT
copy /Y "!CONNECTOR_DIR!\config.example.json" "!CONNECTOR_CONFIG!" >nul
echo          [OK] Created !CONNECTOR_CONFIG!.
exit /b 0

:SEED_DEFAULT
call :write_default_connector_config
exit /b 0

:write_default_connector_config
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
    echo       "resume_from_bookmark": true
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

:CONNECTOR_ALREADY
echo          [OK] Connector service is already running.
exit /b 0

:CONNECTOR_INSTALL
echo          Installing connector service...
!PY_LAUNCHER! "!CONNECTOR_DIR!\install_service.py" --config "!CONNECTOR_CONFIG!" >>"%INSTALL_LOG%" 2>&1
set "INST_RC=!ERRORLEVEL!"
if "!INST_RC!"=="0" goto CONNECTOR_VERIFY
timeout /t 2 /nobreak >nul
!PY_LAUNCHER! "!CONNECTOR_DIR!\install_service.py" --config "!CONNECTOR_CONFIG!" >>"%INSTALL_LOG%" 2>&1
set "INST_RC=!ERRORLEVEL!"
if "!INST_RC!"=="0" goto CONNECTOR_VERIFY
color 0E
echo          [!!] Connector install failed ^(rc=!INST_RC!^).
echo               ULPF will still start but host log streaming is off.
color 0B
exit /b 0

:CONNECTOR_VERIFY
timeout /t 3 /nobreak >nul
call :query_connector_status
if "!SVC_LINE!"=="connector.service.status=installed,running" goto CONNECTOR_OK

:: If scheduled task is not running, spawn directly in background so it runs before backend
start "ULPF Connector" /MIN cmd /c "!PY_LAUNCHER! ""!CONNECTOR_DIR!\connector.py"" --config ""!CONNECTOR_CONFIG!"""
echo          [OK] Connector running in background, waiting for backend.
exit /b 0

:CONNECTOR_OK
echo          [OK] Connector service installed and running.
exit /b 0

:: ============================================================
:: Drawing
:: ============================================================
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
echo        [1]  Docker      ^(recommended - no local installs^)
echo        [2]  Local       ^(uses existing Python + Node^)
echo        [3]  Exit
echo   ------------------------------------------------------------
echo.
exit /b 0

:draw_step
echo.
echo   [%~1/2]  %~2...
exit /b 0