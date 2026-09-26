@echo off
setlocal EnableDelayedExpansion EnableExtensions
title ULPF Local
color 0B

:: ============================================================
::  ULPF - Local Worker
::
::  Called by start_ulpf.bat after the connector is installed.
::  Responsibilities:
::    1. Write .env from scripts\.env.local
::       (SQLite, memory:// Redis, local file storage)
::    2. Create venv, pip install, npm install
::    3. Bootstrap SQLite schema + seed
::    4. Spawn backend + frontend windows
::    5. Wait for readiness, open browser, control console
:: ============================================================

set "SCRIPTS_DIR=%~dp0"
if "!SCRIPTS_DIR:~-1!"=="\" set "SCRIPTS_DIR=!SCRIPTS_DIR:~0,-1!"
for %%I in ("!SCRIPTS_DIR!\..") do set "REPO_ROOT=%%~fI"

set "ULPF_HOME=%USERPROFILE%\.ulpf"
if not exist "%ULPF_HOME%" mkdir "%ULPF_HOME%" >nul 2>&1
set "INSTALL_LOG=%ULPF_HOME%\install.log"

set "ENV_TEMPLATE=!SCRIPTS_DIR!\.env.local"
set "ENV_TARGET=!REPO_ROOT!\.env"

:: ============================================================
:: 0. Python detection
:: ============================================================
set "PY_LAUNCHER="
set "PY_VER="
call :detect_python
if "!PY_LAUNCHER!"=="" goto NO_PY

:: ============================================================
:: 1. Write .env for Local
:: ============================================================
cls
echo.
echo   ============================================================
echo.
echo        U L P F   -   L O C A L   M O D E
echo.
echo   ============================================================
echo.
echo     Python: !PY_VER!  ^(!PY_LAUNCHER!^)
echo.
call :say "Preparing .env for Local..."

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
echo          [OK] .env written from scripts\.env.local

:: ============================================================
:: 2. venv + deps
:: ============================================================
cd /d "!REPO_ROOT!"

set "VENV_PY=!REPO_ROOT!\backend\venv\Scripts\python.exe"

if not exist "!VENV_PY!" (
    call :say "Creating Python venv with !PY_LAUNCHER!..."
    if exist "!REPO_ROOT!\backend\venv" rmdir /s /q "!REPO_ROOT!\backend\venv" >nul 2>&1
    !PY_LAUNCHER! -m venv "!REPO_ROOT!\backend\venv"
    if not exist "!VENV_PY!" goto VENV_FAIL
    echo          [OK] venv created.
)

call :say "Installing backend dependencies..."
"!VENV_PY!" -m pip install --disable-pip-version-check --no-cache-dir --default-timeout=100 --retries=8 -r "!REPO_ROOT!\backend\requirements.txt" >>"%INSTALL_LOG%" 2>&1
if errorlevel 1 goto PIP_FAIL
echo          [OK] Backend dependencies installed.

if exist "!REPO_ROOT!\backend\requirements-optional.txt" (
    "!VENV_PY!" -m pip install --disable-pip-version-check --no-cache-dir --default-timeout=100 --retries=8 -r "!REPO_ROOT!\backend\requirements-optional.txt" >>"%INSTALL_LOG%" 2>&1
    echo          [OK] Optional dependencies done.
)

:: ============================================================
:: 3. Bootstrap SQLite schema + seed
:: ============================================================
call :say "Bootstrapping local database..."

(
    echo import sys
    echo sys.path.insert^(0, r'!REPO_ROOT!\backend'^)
    echo from app.db.base import Base
    echo from app.db.session import engine
    echo Base.metadata.create_all^(bind=engine^)
    echo from app.db.init_db import init_db
    echo init_db^(^)
    echo print^('BOOTSTRAP_OK'^)
) >"%TEMP%\ulpf_bootstrap.py"

pushd "!REPO_ROOT!\backend"
"!VENV_PY!" "%TEMP%\ulpf_bootstrap.py" >>"%INSTALL_LOG%" 2>&1
set "RC=!ERRORLEVEL!"
popd
del "%TEMP%\ulpf_bootstrap.py" >nul 2>&1

if not "!RC!"=="0" goto DB_FAIL
echo          [OK] Database schema + seed data ready.

:: ============================================================
:: 4. Frontend deps
:: ============================================================
if not exist "!REPO_ROOT!\frontend\node_modules" (
    call :say "Installing frontend dependencies..."
    pushd "!REPO_ROOT!\frontend"
    call npm install >>"%INSTALL_LOG%" 2>&1
    set "RC=!ERRORLEVEL!"
    popd
    if not "!RC!"=="0" goto NPM_FAIL
    echo          [OK] Frontend dependencies installed.
)

:: ============================================================
:: 5. Spawn backend + frontend windows
:: ============================================================
call :say "Starting backend window..."
start "ULPF Backend" cmd /k "cd /d ""!REPO_ROOT!\backend"" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

call :say "Starting frontend window..."
start "ULPF Frontend" cmd /k "cd /d ""!REPO_ROOT!\frontend"" && npm run dev"

:: ============================================================
:: 6. Wait for readiness
:: ============================================================
call :wait_for_ready
if errorlevel 1 goto WAIT_TIMEOUT

:: ============================================================
:: 7. Control console
:: ============================================================
goto CONTROL_LOOP

:: ============================================================
:: ERROR PATHS
:: ============================================================
:NO_TEMPLATE
color 0C
echo.
echo          ERROR: scripts\.env.local not found.
pause
exit /b 1

:NO_PY
color 0C
echo.
echo          ERROR: no supported Python found.
pause
exit /b 1

:VENV_FAIL
color 0C
echo.
echo          ERROR: venv creation failed.
pause
exit /b 1

:PIP_FAIL
color 0C
echo.
echo          ERROR: pip install failed. See %INSTALL_LOG%.
powershell -NoProfile -Command "Get-Content '%INSTALL_LOG%' -Tail 20"
pause
exit /b 1

:DB_FAIL
color 0C
echo.
echo          ERROR: SQLite bootstrap failed. See %INSTALL_LOG%.
powershell -NoProfile -Command "Get-Content '%INSTALL_LOG%' -Tail 30"
pause
exit /b 1

:NPM_FAIL
color 0C
echo.
echo          ERROR: npm install failed. See %INSTALL_LOG%.
powershell -NoProfile -Command "Get-Content '%INSTALL_LOG%' -Tail 20"
pause
exit /b 1

:WAIT_TIMEOUT
color 0E
cls
echo.
echo   ============================================================
echo     ULPF DID NOT BECOME READY
echo   ============================================================
echo.
echo     Frontend 5173:
powershell -NoProfile -Command ^
    "try { $r=Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2; Write-Host ('      HTTP ' + $r.StatusCode) } catch { Write-Host '      NOT RESPONDING' }"
echo.
echo     Backend 8000:
powershell -NoProfile -Command ^
    "try { $r=Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing -TimeoutSec 2; Write-Host ('      HTTP ' + $r.StatusCode) } catch { Write-Host '      NOT RESPONDING' }"
echo.
echo     See the "ULPF Backend" and "ULPF Frontend" windows.
echo     Full log: %INSTALL_LOG%
echo.
pause
call :shutdown_now
exit /b 1

:: ============================================================
:: CONTROL LOOP
:: ============================================================
:CONTROL_LOOP
echo.
echo          Opening browser...
start "" "http://localhost:5173"
call :draw_console

:CONTROL_TICK
choice /c qslohrbc /n /t 5 /d s /m "ulpf-local> " >nul 2>&1
set "CE=!ERRORLEVEL!"

if "!CE!"=="1" goto SHUTDOWN
if "!CE!"=="2" call :draw_console
if "!CE!"=="3" call :CTL_LOGS
if "!CE!"=="4" start "" "http://localhost:5173"
if "!CE!"=="5" call :CTL_HELP
if "!CE!"=="6" call :CTL_RESTART
if "!CE!"=="7" call :CTL_REBUILD
if "!CE!"=="8" cls & call :draw_console
goto CONTROL_TICK

:CTL_LOGS
cls
echo.
echo   Local mode: check the "ULPF Backend" window for logs.
echo.
pause >nul
call :draw_console
goto CONTROL_TICK

:CTL_HELP
cls
echo.
echo   s - status   l - logs   o - open browser
echo   h - help     r - restart windows
echo   b - reinstall deps   c - clear   q - quit
echo.
pause >nul
call :draw_console
goto CONTROL_TICK

:CTL_RESTART
call :say "Restarting local windows..."
taskkill /FI "WINDOWTITLE eq ULPF Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ULPF Frontend*" /T /F >nul 2>&1
timeout /t 2 /nobreak >nul
start "ULPF Backend" cmd /k "cd /d ""!REPO_ROOT!\backend"" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "ULPF Frontend" cmd /k "cd /d ""!REPO_ROOT!\frontend"" && npm run dev"
call :draw_console
goto CONTROL_TICK

:CTL_REBUILD
echo.
set /p "RBOK=   Reinstall Python + Node dependencies? [y/N]: "
if /i not "!RBOK!"=="y" goto CONTROL_TICK
call :say "Reinstalling backend deps..."
"!VENV_PY!" -m pip install --disable-pip-version-check --no-cache-dir --default-timeout=100 --retries=8 -r "!REPO_ROOT!\backend\requirements.txt" >>"%INSTALL_LOG%" 2>&1
call :say "Reinstalling frontend deps..."
pushd "!REPO_ROOT!\frontend"
call npm install >>"%INSTALL_LOG%" 2>&1
popd
call :draw_console
goto CONTROL_TICK

:SHUTDOWN
color 0E
cls
echo.
echo   Stopping local windows...
call :shutdown_now
color 0A
echo.
echo   ULPF stopped. Closing in 3 seconds.
timeout /t 3 /nobreak >nul
exit

:shutdown_now
taskkill /FI "WINDOWTITLE eq ULPF Backend*" /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq ULPF Frontend*" /T >nul 2>&1
timeout /t 2 /nobreak >nul
taskkill /FI "WINDOWTITLE eq ULPF Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ULPF Frontend*" /T /F >nul 2>&1
exit /b 0

:: ============================================================
:: HELPERS
:: ============================================================
:say
echo   [*] %~1
exit /b 0

:detect_python
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
    "try { $c = New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8000); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
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
echo     ULPF Local is starting...
echo   ============================================================
echo.
echo     Progress: [!BAR!] !PCT!%%
echo.
echo     Waiting for frontend + backend...
echo.
timeout /t 2 /nobreak >nul
goto WFR_LOOP

:draw_console
cls
echo.
echo   ============================================================
echo                U L P F   L O C A L   R U N N I N G
echo   ============================================================
echo.
echo     Frontend:  http://localhost:5173
echo     API:       http://localhost:8000
echo     API Docs:  http://localhost:8000/docs
echo.
echo     Database:  backend\ulpf_local.db  ^(SQLite^)
echo     Redis:     memory://              ^(in-process^)
echo     Storage:   backend\data\raw\      ^(local files^)
echo.
echo     Login:     admin@ulpf.local / ChangeMe_Admin123!
echo.
echo   ------------------------------------------------------------
echo     Commands
echo   ------------------------------------------------------------
echo       s   status
echo       l   logs  ^(check the ULPF Backend window^)
echo       o   open browser
echo       h   help
echo       r   restart windows
echo       b   reinstall deps
echo       c   clear
echo       q   quit
echo.
exit /b 0