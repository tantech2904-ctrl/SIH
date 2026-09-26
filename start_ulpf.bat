@echo off
setlocal EnableDelayedExpansion EnableExtensions
title ULPF Control
color 0B
chcp 65001 >nul 2>&1

:: ============================================================
::  ULPF - Universal Log Pre-Processing Framework
::  Fully automatic setup + control console.
::
::  Robustness features:
::    - Adaptive readiness: only requires frontend + backend to
::      respond. Login and Redis are tolerated as non-blocking.
::    - Auto-recovery: retries restarting the backend if it does
::      not become healthy within the first 60 seconds.
::    - Auto-fix Redis: if Redis is unreachable in local mode, it
::      writes REDIS_URL=memory:// to .env and restarts backend.
::    - Diagnostic on timeout: prints endpoint results and tail
::      of install.log so failures are debuggable.
::
::  If something is fundamentally broken, run cleanup_ulpf.bat.
:: ============================================================

:: ============================================================
:: ELEVATION
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
set "BACKEND_RETRIES=0"

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
:: STEP 1 - MODE SELECTION
:: ============================================================
:STEP_MODE
if not "!ARG_MODE!"=="" goto MODE_AUTO

call :draw_mode_menu
set /p "CHOICE=          Enter choice [1/2/3]: "
goto MODE_RESOLVE

:MODE_AUTO
set "CHOICE=!ARG_MODE!"

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
:: Mode validation - Docker
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
:: Mode validation - Local
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
echo               Installed Python versions detected by the py launcher:
py -0p 2>nul
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
call :backup_env_with_timestamp
exit /b 0

:backup_env_with_timestamp
set "TS="
for /f "usebackq tokens=*" %%T in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd-HHmmss'"`) do set "TS=%%T"
if "!TS!"=="" set "TS=backup"
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
:: Validate .env critical vars
:: ------------------------------------------------------------
:validate_env_critical
set "ENV_CHANGED=0"
set "ENV_FILE=!REPO_ROOT!\.env"

if not exist "!ENV_FILE!" goto VALIDATE_ENV_SKIP

call :ensure_env_var "POSTGRES_USER"
call :ensure_env_var "POSTGRES_PASSWORD"
call :ensure_env_var "POSTGRES_DB"

call :fix_empty_postgres_password

if "!ENV_CHANGED!"=="1" (
    echo          [OK] .env patched with required values.
    call :log ".env auto-patched with missing POSTGRES_ vars"
)
exit /b 0

:VALIDATE_ENV_SKIP
echo          [--] .env not found, skipping validation.
exit /b 0

:ensure_env_var
set "VARNAME=%~1"
findstr /B /C:"!VARNAME!=" "!ENV_FILE!" >nul 2>&1
if not errorlevel 1 exit /b 0
echo          [!!] Missing !VARNAME! - adding default.
powershell -NoProfile -Command "Add-Content -LiteralPath '!ENV_FILE!' -Value '!VARNAME!=ulpf'"
set "ENV_CHANGED=1"
exit /b 0

:fix_empty_postgres_password
findstr /R /C:"^POSTGRES_PASSWORD= *$" "!ENV_FILE!" >nul 2>&1
if errorlevel 1 exit /b 0
echo          [!!] POSTGRES_PASSWORD is empty - fixing.
powershell -NoProfile -Command ^
    "$p = '!ENV_FILE!'; $c = Get-Content -Raw -LiteralPath $p; $c = $c -replace 'POSTGRES_PASSWORD=\s*\r?\n','POSTGRES_PASSWORD=ulpf' + [Environment]::NewLine; Set-Content -LiteralPath $p -Value $c -NoNewline -Encoding UTF8"
set "ENV_CHANGED=1"
exit /b 0

:: ------------------------------------------------------------
:: Validate .env matches the chosen mode
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
    "$p = '!REPO_ROOT!\.env'; $c = Get-Content -Raw -LiteralPath $p; $c = $c -replace '@postgres:','@localhost:'; $c = $c -replace '@redis:','@localhost:'; $c = $c -replace 'MINIO_ENDPOINT=minio:','MINIO_ENDPOINT=localhost:'; Set-Content -LiteralPath $p -Value $c -NoNewline -Encoding UTF8"
echo          [OK] .env patched for local mode.
call :log "Local-mode .env had Docker hostnames; patched to localhost"
color 0B
exit /b 0

:VALIDATE_MODE_DOCKER
exit /b 0

:: ------------------------------------------------------------
:: Validate migrations
:: ------------------------------------------------------------
:validate_migrations
set "MIG_BAD=0"

if not exist "!REPO_ROOT!\backend\alembic\versions\0001_initial.py" exit /b 0

findstr /C:"insp.get_table_names" "!REPO_ROOT!\backend\alembic\versions\0001_initial.py" >nul 2>&1
if not errorlevel 1 goto VALIDATE_MIGRATIONS_OK

findstr /C:"Base.metadata.create_all" "!REPO_ROOT!\backend\alembic\versions\0001_initial.py" >nul 2>&1
if errorlevel 1 goto VALIDATE_MIGRATIONS_OK

set "MIG_BAD=1"

:VALIDATE_MIGRATIONS_OK
if "!MIG_BAD!"=="1" call :show_migration_warning
exit /b 0

:show_migration_warning
color 0E
echo.
echo   ------------------------------------------------------------
echo     WARNING: 0001_initial.py uses unguarded create_all()
echo     This causes DuplicateTable errors on restart. Wrap it
echo     in an existence check.
echo   ------------------------------------------------------------
color 0B
call :log "WARN: 0001_initial.py still has unguarded create_all()"
exit /b 0

:: ============================================================
:: STEP 3 - CONNECTOR SERVICE
:: ============================================================
:STEP_CONNECTOR
if "!ARG_NO_CONNECTOR!"=="1" goto CONNECTOR_SKIPPED
call :draw_step 3 "Host log connector"
echo.
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

if "!PY_LAUNCHER!"=="" goto LOCAL_NO_PY_LAUNCHER

echo          Using Python: !PY_LAUNCHER!
echo          Repo root:    !REPO_ROOT!

if not exist "!REPO_ROOT!\backend\requirements.txt" goto LOCAL_NO_REQS

if not exist "!REPO_ROOT!\backend\venv\Scripts\python.exe" goto LOCAL_NEED_VENV
goto LOCAL_VENV_READY

:LOCAL_NO_PY_LAUNCHER
color 0C
echo          ERROR: No supported Python launcher detected.
call :log "FATAL: PY_LAUNCHER empty at START_LOCAL"
pause
exit /b 1

:LOCAL_NO_REQS
color 0C
echo          ERROR: backend\requirements.txt not found.
call :log "FATAL: requirements.txt missing"
pause
exit /b 1

:LOCAL_NEED_VENV
call :create_venv
if errorlevel 1 goto LOCAL_VENV_FAILED

:LOCAL_VENV_READY
if not exist "!REPO_ROOT!\backend\venv\Scripts\python.exe" goto LOCAL_VENV_MISSING

call :install_backend_deps
if errorlevel 1 goto LOCAL_PIP_FAILED

call :bootstrap_local_db
if errorlevel 1 goto LOCAL_DB_FAILED

call :install_frontend_deps
if errorlevel 1 goto LOCAL_NPM_FAILED

:: Auto-fix Redis for local mode: prefer memory:// when no local Redis
call :autofix_redis_local

call :spawn_local_windows

call :log "Spawned backend and frontend windows"
call :write_marker
goto WAIT_FOR_READY

:LOCAL_VENV_MISSING
color 0C
echo          ERROR: backend\venv\Scripts\python.exe not found after venv step.
call :log "FATAL: venv python missing"
pause
exit /b 1

:LOCAL_VENV_FAILED
color 0C
echo.
echo          ERROR: venv creation failed.
echo          Check %INSTALL_LOG% for details.
call :log "FATAL: venv creation failed"
pause
exit /b 1

:LOCAL_PIP_FAILED
color 0C
echo.
echo          ERROR: pip install failed.
echo          Check %INSTALL_LOG% for details.
call :log "FATAL: pip install failed"
pause
exit /b 1

:LOCAL_DB_FAILED
color 0C
echo.
echo          ERROR: database bootstrap failed.
echo          Check %INSTALL_LOG% for details.
call :log "FATAL: local db bootstrap failed"
pause
exit /b 1

:LOCAL_NPM_FAILED
color 0C
echo.
echo          ERROR: npm install failed.
echo          Check %INSTALL_LOG% for details.
call :log "FATAL: npm install failed"
pause
exit /b 1

:: ------------------------------------------------------------
:: :spawn_local_windows
:: ------------------------------------------------------------
:spawn_local_windows
echo          Starting backend window...
start "ULPF Backend" cmd /k "cd /d ""!REPO_ROOT!\backend"" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo          Starting frontend window...
start "ULPF Frontend" cmd /k "cd /d ""!REPO_ROOT!\frontend"" && npm run dev"
exit /b 0

:: ------------------------------------------------------------
:: :autofix_redis_local
::
:: If REDIS_URL is not memory:// and no Redis is reachable on
:: localhost:6379, patch .env to use memory:// so the backend
:: does not waste 30+ seconds waiting for a timeout on every
:: request. This is local-mode-only.
:: ------------------------------------------------------------
:autofix_redis_local
set "REDIS_URL="
set "REDIS_TMP=%TEMP%\ulpf_redisurl.txt"
if exist "!REDIS_TMP!" del "!REDIS_TMP!" >nul 2>&1

powershell -NoProfile -Command ^
    "$line = Get-Content -LiteralPath '!REPO_ROOT!\.env' -ErrorAction SilentlyContinue | Where-Object { $_ -match 'REDIS_URL' } | Select-Object -First 1; if ($line) { ($line -split '=',2)[1].Trim() | Set-Content -LiteralPath '!REDIS_TMP!' -NoNewline -Encoding ascii }"

if exist "!REDIS_TMP!" (
    set /p "REDIS_URL="<"!REDIS_TMP!"
    del "!REDIS_TMP!" >nul 2>&1
)
if defined REDIS_URL set "REDIS_URL=!REDIS_URL:"=!"

if "!REDIS_URL!"=="" goto AUTOFIX_REDIS_DONE
if /i "!REDIS_URL!"=="memory://" goto AUTOFIX_REDIS_DONE

:: Is a local Redis reachable?
powershell -NoProfile -Command ^
    "try { $c = New-Object System.Net.Sockets.TcpClient; $c.Connect('localhost',6379); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto AUTOFIX_REDIS_DONE

echo          [!!] No local Redis detected - switching to memory:// for local mode.
call :log "Local mode: no Redis, switching to memory://"

powershell -NoProfile -Command ^
    "$p = '!REPO_ROOT!\.env'; $c = Get-Content -LiteralPath $p; $c = $c -notmatch '^REDIS_URL='; $c += 'REDIS_URL=memory://'; Set-Content -LiteralPath $p -Value $c -Encoding UTF8"

echo          [OK] .env updated: REDIS_URL=memory://

:AUTOFIX_REDIS_DONE
exit /b 0

:: ------------------------------------------------------------
:: :create_venv
:: ------------------------------------------------------------
:create_venv
echo          Creating Python virtual environment with !PY_LAUNCHER!...

if exist "!REPO_ROOT!\backend\venv" (
    echo          Removing stale venv directory...
    rmdir /s /q "!REPO_ROOT!\backend\venv" >nul 2>&1
)

!PY_LAUNCHER! -m venv "!REPO_ROOT!\backend\venv"
set "RC=!ERRORLEVEL!"

if not "!RC!"=="0" goto VENV_FAILED
if not exist "!REPO_ROOT!\backend\venv\Scripts\python.exe" goto VENV_FAILED

echo          [OK] Virtual environment created.
exit /b 0

:VENV_FAILED
call :log "FATAL: venv creation failed"
exit /b 1

:: ------------------------------------------------------------
:: :install_backend_deps
:: ------------------------------------------------------------
:install_backend_deps
echo          Installing core backend dependencies ^(may take a few minutes^)...

set "VENV_PY=!REPO_ROOT!\backend\venv\Scripts\python.exe"

if not exist "!VENV_PY!" goto PIP_NO_VENV_PY
if not exist "!REPO_ROOT!\backend\requirements.txt" goto PIP_NO_REQS

echo          Running: pip install -r requirements.txt
"!VENV_PY!" -m pip install --disable-pip-version-check --no-cache-dir --default-timeout=100 --retries=8 -r "!REPO_ROOT!\backend\requirements.txt" >>"%INSTALL_LOG%" 2>&1
set "RC=!ERRORLEVEL!"

if not "!RC!"=="0" goto PIP_CORE_FAILED

echo          [OK] Core dependencies installed.
echo          Installing optional dependencies ^(may be skipped^)...

if not exist "!REPO_ROOT!\backend\requirements-optional.txt" goto PIP_OPTIONAL_SKIPPED

"!VENV_PY!" -m pip install --disable-pip-version-check --no-cache-dir --default-timeout=100 --retries=8 -r "!REPO_ROOT!\backend\requirements-optional.txt" >>"%INSTALL_LOG%" 2>&1
if errorlevel 1 goto PIP_OPTIONAL_FAILED
echo          [OK] Optional dependencies installed.
exit /b 0

:PIP_OPTIONAL_SKIPPED
echo          [--] requirements-optional.txt not present, skipping.
exit /b 0

:PIP_OPTIONAL_FAILED
color 0E
echo          [!!] Optional dependencies failed ^(non-fatal^).
call :log "WARN: optional dependencies failed"
exit /b 0

:PIP_NO_VENV_PY
color 0C
echo          ERROR: venv python missing.
call :log "FATAL: venv python missing before pip install"
exit /b 1

:PIP_NO_REQS
color 0C
echo          ERROR: requirements.txt missing.
call :log "FATAL: requirements.txt missing"
exit /b 1

:PIP_CORE_FAILED
color 0C
echo          ERROR: pip install failed with code !RC!.
echo          Last 20 lines of %INSTALL_LOG%:
echo          ------------------------------------------------
powershell -NoProfile -Command "Get-Content '%INSTALL_LOG%' -Tail 20"
echo          ------------------------------------------------
call :log "FATAL: pip install failed rc=!RC!"
exit /b 1

:: ------------------------------------------------------------
:: :bootstrap_local_db
:: ------------------------------------------------------------
:bootstrap_local_db
echo          Preparing database schema...

set "VENV_PY=!REPO_ROOT!\backend\venv\Scripts\python.exe"
if not exist "!VENV_PY!" goto DB_NO_VENV_PY

set "DB_URL="
set "DB_TMP=%TEMP%\ulpf_dburl.txt"
if exist "!DB_TMP!" del "!DB_TMP!" >nul 2>&1

powershell -NoProfile -Command ^
    "$line = Get-Content -LiteralPath '!REPO_ROOT!\.env' -ErrorAction SilentlyContinue | Where-Object { $_ -match 'DATABASE_URL' } | Select-Object -First 1; if ($line) { ($line -split '=',2)[1].Trim() | Set-Content -LiteralPath '!DB_TMP!' -NoNewline -Encoding ascii }"

if exist "!DB_TMP!" (
    set /p "DB_URL="<"!DB_TMP!"
    del "!DB_TMP!" >nul 2>&1
)
if defined DB_URL set "DB_URL=!DB_URL:"=!"

if "!DB_URL!"=="" goto DB_DEFAULT_SQLITE

echo          DATABASE_URL = !DB_URL!

set "DETECT=!DB_URL:~0,9!"
if /i "!DETECT!"=="sqlite://" goto DB_SQLITE

set "DETECT=!DB_URL:~0,14!"
if /i "!DETECT!"=="sqlite+pysqlite" goto DB_SQLITE

goto DB_POSTGRES

:DB_DEFAULT_SQLITE
echo          [!!] DATABASE_URL not found in .env - defaulting to SQLite.
set "DB_URL=sqlite:///./ulpf_local.db"
powershell -NoProfile -Command "Add-Content -LiteralPath '!REPO_ROOT!\.env' -Value 'DATABASE_URL=sqlite:///./ulpf_local.db'"
echo          DATABASE_URL = !DB_URL!
goto DB_SQLITE

:DB_SQLITE
echo          SQLite detected - bootstrapping via create_all + seed.

(
    echo import sys
    echo sys.path.insert^(0, r'!REPO_ROOT!\backend'^)
    echo from app.db.base import Base
    echo from app.db.session import engine
    echo Base.metadata.create_all^(bind=engine^)
    echo from app.db.init_db import init_db
    echo init_db^(^)
    echo print^('OK'^)
) >"%TEMP%\ulpf_bootstrap.py"

pushd "!REPO_ROOT!\backend"
"!VENV_PY!" "%TEMP%\ulpf_bootstrap.py" >>"%INSTALL_LOG%" 2>&1
set "RC=!ERRORLEVEL!"
popd
del "%TEMP%\ulpf_bootstrap.py" >nul 2>&1

if not "!RC!"=="0" goto DB_BOOTSTRAP_FAILED
echo          [OK] SQLite schema + seed data ready.
exit /b 0

:DB_POSTGRES
echo          Postgres detected - running alembic upgrade head.

if not exist "!REPO_ROOT!\backend\alembic\alembic.ini" goto DB_NO_ALEMBIC_INI

pushd "!REPO_ROOT!\backend"
"!VENV_PY!" -m alembic -c "alembic\alembic.ini" upgrade head >>"%INSTALL_LOG%" 2>&1
set "RC=!ERRORLEVEL!"
popd

if not "!RC!"=="0" goto DB_ALEMBIC_FAILED
echo          [OK] Database migrations applied.
exit /b 0

:DB_NO_VENV_PY
color 0C
echo          ERROR: venv python missing for db bootstrap.
call :log "FATAL: db bootstrap - venv python missing"
exit /b 1

:DB_NO_ALEMBIC_INI
color 0C
echo          ERROR: alembic.ini not found.
call :log "FATAL: alembic.ini missing"
exit /b 1

:DB_BOOTSTRAP_FAILED
color 0C
echo          ERROR: SQLite bootstrap failed with code !RC!.
echo          Last 25 lines of %INSTALL_LOG%:
echo          ------------------------------------------------
powershell -NoProfile -Command "Get-Content '%INSTALL_LOG%' -Tail 25"
echo          ------------------------------------------------
call :log "FATAL: sqlite bootstrap failed rc=!RC!"
exit /b 1

:DB_ALEMBIC_FAILED
color 0C
echo          ERROR: alembic upgrade failed with code !RC!.
echo          Last 25 lines of %INSTALL_LOG%:
echo          ------------------------------------------------
powershell -NoProfile -Command "Get-Content '%INSTALL_LOG%' -Tail 25"
echo          ------------------------------------------------
call :log "FATAL: alembic upgrade failed rc=!RC!"
exit /b 1

:: ------------------------------------------------------------
:: :install_frontend_deps
:: ------------------------------------------------------------
:install_frontend_deps
if exist "!REPO_ROOT!\frontend\node_modules" exit /b 0

echo          Installing frontend dependencies ^(may take a few minutes^)...

pushd "!REPO_ROOT!\frontend"
call npm install >>"%INSTALL_LOG%" 2>&1
set "RC=!ERRORLEVEL!"
popd

if not "!RC!"=="0" goto NPM_FAILED
echo          [OK] Frontend dependencies installed.
exit /b 0

:NPM_FAILED
color 0C
echo          ERROR: npm install failed with code !RC!.
echo          Last 20 lines of %INSTALL_LOG%:
echo          ------------------------------------------------
powershell -NoProfile -Command "Get-Content '%INSTALL_LOG%' -Tail 20"
echo          ------------------------------------------------
call :log "FATAL: npm install failed rc=!RC!"
exit /b 1

:: ============================================================
:: WAIT FOR READY - ADAPTIVE
::
:: Only requires:
::   1. Frontend responds on http://localhost:5173
::   2. Backend health endpoint responds with HTTP 200
::
:: Does NOT require:
::   - Redis to be up          (reported as "ready": false is OK)
::   - Login endpoint to pass  (PS 5.1 quirk made this unreliable)
::
:: Fallback chain per tick:
::   1. Try /api/v1/health/ready - success if HTTP 200
::   2. Fall back to /api/v1/health - success if HTTP 200
::   3. Fall back to TCP probe on 127.0.0.1:8000 - success if
::      connection succeeds
::
:: Auto-recovery:
::   - At TICKS=30 (~60s), if backend is not responding, kill and
::     respawn the backend window once. At TICKS=60 (~120s), try
::     once more. After that, just keep waiting.
:: ============================================================
:WAIT_FOR_READY
color 0B
set /a TICKS=0
set /a MAX_TICKS=150
set /a BACKEND_RETRIES=0

:WAIT_LOOP
set /a TICKS+=1

if !TICKS! GTR %MAX_TICKS% goto WAIT_TIMEOUT

:: --- Auto-recovery check ---
if !TICKS!==30 call :try_backend_recovery
if !TICKS!==60 call :try_backend_recovery

set "READY=0"

:: --- Frontend check ---
powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto WAIT_DRAW

:: --- Backend check (3-level fallback) ---
call :probe_backend
if not "!BACKEND_UP!"=="1" goto WAIT_DRAW

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

:: ------------------------------------------------------------
:: :probe_backend
:: Sets BACKEND_UP=1 if any of the three probes succeed.
:: ------------------------------------------------------------
:probe_backend
set "BACKEND_UP=0"

:: Probe 1 - health/ready
powershell -NoProfile -Command ^
    "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 set "BACKEND_UP=1" & exit /b 0

:: Probe 2 - plain /health
powershell -NoProfile -Command ^
    "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 set "BACKEND_UP=1" & exit /b 0

:: Probe 3 - TCP port 8000 open
powershell -NoProfile -Command ^
    "try { $c = New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8000); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 set "BACKEND_UP=1" & exit /b 0

exit /b 0

:: ------------------------------------------------------------
:: :try_backend_recovery
:: Kills stray python processes from prior runs, respawns the
:: backend window. Only runs in local mode. Gives up after 2 tries.
:: ------------------------------------------------------------
:try_backend_recovery
if not "!MODE!"=="local" exit /b 0
if !BACKEND_RETRIES! GEQ 2 exit /b 0

:: Is the backend already up? Then no recovery needed.
call :probe_backend
if "!BACKEND_UP!"=="1" exit /b 0

set /a BACKEND_RETRIES+=1
call :log "Backend recovery attempt !BACKEND_RETRIES!"

color 0E
echo.
echo          [!!] Backend not responding yet - restarting it (attempt !BACKEND_RETRIES! of 2).
color 0B

:: Kill only OUR windows
taskkill /FI "WINDOWTITLE eq ULPF Backend*" /T /F >nul 2>&1
timeout /t 2 /nobreak >nul

:: Respawn backend only
start "ULPF Backend" cmd /k "cd /d ""!REPO_ROOT!\backend"" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

call :log "Backend respawned"
exit /b 0

:: ------------------------------------------------------------
:: :WAIT_TIMEOUT - diagnostic on failure
:: ------------------------------------------------------------
:WAIT_TIMEOUT
color 0E
cls
call :draw_banner "ULPF DID NOT BECOME READY IN TIME"
echo.
echo     Checked for 300 seconds. Running diagnostics...
echo.

call :diagnose_on_failure

echo.
echo     Full log: %INSTALL_LOG%
echo.
echo     To reset everything: run cleanup_ulpf.bat
echo.
echo     Press any key to close the two spawned windows and exit.
pause >nul
call :shutdown_now
exit /b 1

:: ------------------------------------------------------------
:: :diagnose_on_failure
:: ------------------------------------------------------------
:diagnose_on_failure
echo     --- Frontend (5173) ---
powershell -NoProfile -Command ^
    "try { $r = Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2; Write-Host ('    HTTP ' + $r.StatusCode) } catch { Write-Host '    NOT RESPONDING' }"

echo.
echo     --- Backend /health/ready ---
powershell -NoProfile -Command ^
    "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing -TimeoutSec 2; Write-Host ('    HTTP ' + $r.StatusCode); Write-Host ('    Body: ' + $r.Content.Substring(0, [Math]::Min(200, $r.Content.Length))) } catch { Write-Host '    NOT RESPONDING' }"

echo.
echo     --- Port status ---
powershell -NoProfile -Command ^
    "$ports = netstat -ano | Select-String ':5173|:8000'; if ($ports) { $ports | ForEach-Object { Write-Host ('    ' + $_.ToString().Trim()) } } else { Write-Host '    Neither port 5173 nor 8000 is listening.' }"

echo.
echo     --- Backend process ---
powershell -NoProfile -Command ^
    "$py = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*SIH-main*' }; if ($py) { $py | ForEach-Object { Write-Host ('    PID ' + $_.Id + '  ' + $_.Path) } } else { Write-Host '    No backend python process found.' }"

echo.
echo     --- Last 20 lines of install.log ---
powershell -NoProfile -Command ^
    "if (Test-Path '%INSTALL_LOG%') { Get-Content '%INSTALL_LOG%' -Tail 20 | ForEach-Object { Write-Host ('    ' + $_) } } else { Write-Host '    (no log)' }"
exit /b 0

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
:: ------------------------------------------------------------
:check_python
set "PY_LAUNCHER="
set "PY_VER="

call :try_python "py -3.12"
if not "!PY_LAUNCHER!"=="" goto CHECK_PY_DONE

call :try_python "py -3.11"
if not "!PY_LAUNCHER!"=="" goto CHECK_PY_DONE

call :try_python "py -3.10"
if not "!PY_LAUNCHER!"=="" goto CHECK_PY_DONE

call :try_python "python"
if not "!PY_LAUNCHER!"=="" goto CHECK_PY_DONE

call :try_python "python3"
if not "!PY_LAUNCHER!"=="" goto CHECK_PY_DONE

goto CHECK_PY_MISSING

:CHECK_PY_DONE
echo          [OK] !PY_VER!  ^(launcher: !PY_LAUNCHER!^)
call :log "Python detected: !PY_VER! via !PY_LAUNCHER!"
exit /b 0

:CHECK_PY_MISSING
echo          [--] Python 3.10 / 3.11 / 3.12 not found.
call :log "Python not found (3.10-3.12 required)"
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

:: ------------------------------------------------------------
:: Node detection
:: ------------------------------------------------------------
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

for /f "usebackq tokens=*" %%T in (`powershell -NoProfile -Command "[int][double]::Parse((Get-Date -UFormat %%s))"`) do set "NOW_TS=%%T"
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
    "$p = '!REPO_ROOT!\.env'; $c = Get-Content -Raw -LiteralPath $p; " ^
    "$c = $c -replace 'DATABASE_URL=postgresql\+psycopg://ulpf:ulpf@localhost:5432/ulpf','DATABASE_URL=postgresql+psycopg://ulpf:ulpf@postgres:5432/ulpf'; " ^
    "$c = $c -replace 'REDIS_URL=redis://localhost:6379/0','REDIS_URL=redis://redis:6379/0'; " ^
    "$c = $c -replace 'MINIO_ENDPOINT=localhost:9000','MINIO_ENDPOINT=minio:9000'; " ^
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
:: Force rebuild
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
echo        [1]  Docker      ^(recommended - no local installs^)
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
    "try { Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
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
echo       b   Rebuild from scratch.
echo       c   Clear and redraw the console.
echo       q   Stop everything and close this window.
echo.
echo     If something is fundamentally broken, run cleanup_ulpf.bat.
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
call :spawn_local_windows
echo     [OK] Local windows restarted.

:RESTART_DONE
color 0B
timeout /t 2 /nobreak >nul
exit /b 0