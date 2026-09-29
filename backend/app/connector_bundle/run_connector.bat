@echo off
setlocal EnableDelayedExpansion EnableExtensions
title ULPF Host Log Connector
color 0B

:: ============================================================
::  ULPF - Host Log Connector Launcher
::
::  Auto-detects Python, ensures dependencies (httpx, pywin32),
::  ensures user-writable configuration, and starts live streaming.
:: ============================================================

set "CONNECTOR_DIR=%~dp0"
if "!CONNECTOR_DIR:~-1!"=="\" set "CONNECTOR_DIR=!CONNECTOR_DIR:~0,-1!"

if "%ULPF_SERVER_URL%"=="" (
    set "SERVER_URL=http://localhost:8000"
) else (
    set "SERVER_URL=%ULPF_SERVER_URL%"
)

cls
echo ============================================================
echo           U L P F   -   H O S T   C O N N E C T O R
echo ============================================================
echo Target Server: !SERVER_URL!
echo.

:: 1. Detect Python
set "PY_CMD="

call :test_py "py -3.11"
if not "!PY_CMD!"=="" goto PY_FOUND
call :test_py "py -3.12"
if not "!PY_CMD!"=="" goto PY_FOUND
call :test_py "py -3.10"
if not "!PY_CMD!"=="" goto PY_FOUND
call :test_py "python"
if not "!PY_CMD!"=="" goto PY_FOUND
call :test_py "py"
if not "!PY_CMD!"=="" goto PY_FOUND

color 0C
echo [!!] No Python 3 installation detected on PATH.
echo      Please install Python 3.10+ from python.org and check
echo      "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:test_py
set "CANDIDATE=%~1"
%CANDIDATE% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if not errorlevel 1 (
    if "!PY_CMD!"=="" set "PY_CMD=%CANDIDATE%"
)
exit /b 0

:PY_FOUND
echo [*] Using Python: !PY_CMD!

:: 2. Auto-bootstrap connector files if missing (standalone download mode)
if not exist "!CONNECTOR_DIR!\connector.py" (
    echo [*] Downloading connector package from !SERVER_URL!...
    powershell -NoProfile -Command ^
        "$ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '!SERVER_URL!/api/v1/connectors/download/bundle?os=windows' -OutFile '!CONNECTOR_DIR!\bundle.zip' -UseBasicParsing; Expand-Archive -Path '!CONNECTOR_DIR!\bundle.zip' -DestinationPath '!CONNECTOR_DIR!' -Force; Remove-Item '!CONNECTOR_DIR!\bundle.zip' -Force; exit 0 } catch { exit 1 }"
    if errorlevel 1 (
        echo [!!] Failed to auto-download bundle from !SERVER_URL!.
        echo      Please download the full ULPF connector package from the web interface.
        pause
        exit /b 1
    )
    echo [*] Connector package downloaded and extracted.
)

:: 3. Determine safe writable config path
set "USER_ULPF=%USERPROFILE%\.ulpf"
if not exist "!USER_ULPF!" mkdir "!USER_ULPF!" >nul 2>&1

set "CONFIG_PATH=!USER_ULPF!\connector.json"
set "DATA_CONFIG=C:\ProgramData\ULPF\connector.json"

if not exist "!CONFIG_PATH!" (
    if exist "!DATA_CONFIG!" (
        copy /Y "!DATA_CONFIG!" "!CONFIG_PATH!" >nul 2>&1
    ) else if exist "!CONNECTOR_DIR!\config.example.json" (
        copy /Y "!CONNECTOR_DIR!\config.example.json" "!CONFIG_PATH!" >nul 2>&1
    )
)

:: Ensure server URL is configured
if exist "!CONFIG_PATH!" (
    !PY_CMD! -c "import json; p=r'!CONFIG_PATH!'; d=json.load(open(p)); d['ulpf_base']='!SERVER_URL!'; json.dump(d,open(p,'w'),indent=2)" >nul 2>&1
)

:: 3. Check / install dependencies
echo [*] Checking dependencies...
!PY_CMD! -c "import httpx" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing httpx dependency...
    !PY_CMD! -m pip install --quiet --user httpx
    if errorlevel 1 (
        !PY_CMD! -m pip install --quiet httpx
    )
)

!PY_CMD! -c "import win32evtlog" >nul 2>&1
if errorlevel 1 (
    echo [*] Checking optional pywin32 for native Windows Event Log...
    !PY_CMD! -m pip install --quiet --user pywin32 >nul 2>&1
)

:: 4. Normalize config
echo [*] Normalizing connector config...
!PY_CMD! "!CONNECTOR_DIR!\fix_config.py" --path "!CONFIG_PATH!"
if exist "C:\ProgramData\ULPF" (
    copy /Y "!CONFIG_PATH!" "!DATA_CONFIG!" >nul 2>&1
)

echo.
echo ============================================================
echo   ULPF Host Connector: Real-Time Event Log Streaming
echo   Connecting to backend endpoint configured in:
echo   !CONFIG_PATH!
echo   (Default: http://localhost:8000, or point to your cloud IP)
echo   Forward-only timestamp policy active (only new events sent)
echo   Press Ctrl+C to stop.
echo ============================================================
echo.

!PY_CMD! "!CONNECTOR_DIR!\connector.py" --config "!CONFIG_PATH!" --debug-events %*

echo.
echo [*] Connector stopped.
pause
