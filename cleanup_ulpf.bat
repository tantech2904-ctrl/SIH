@echo off
setlocal EnableDelayedExpansion EnableExtensions
title ULPF Cleanup
color 0E
chcp 65001 >nul 2>&1

:: ============================================================
::  ULPF - Cleanup / Reset Script
::
::  Removes:
::    - Docker containers, volumes, networks, images
::    - The connector scheduled task
::    - Connector config (C:\ProgramData\ULPF)
::    - User state (%USERPROFILE%\.ulpf)
::    - .env and .env backups (keeps .env.example)
::    - backend\venv and frontend\node_modules
::    - Local SQLite databases (backend\*.db)
::    - Python caches (__pycache__, .pytest_cache, etc)
::
::  Does NOT touch:
::    - Source code, git history, README files
::    - .env.example, scripts\.env.local.example
::    - config.example.json
::
::  Requires Administrator (for scheduled task deletion).
::
::  Verification uses NO pipes inside for /f substitutions —
::  the previous version crashed with "| was unexpected at this
::  time." because of `for /f ... in (`cmd | filter`)`.
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
echo        U L P F   -   C L E A N U P   (E L E V A T I O N)
echo.
echo   ============================================================
echo.
echo     Cleanup needs Administrator privileges to remove the
echo     connector scheduled task.
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

:: -------------------- Repo root --------------------
set "REPO_ROOT=%~dp0"
if "!REPO_ROOT:~-1!"=="\" set "REPO_ROOT=!REPO_ROOT:~0,-1!"
cd /d "!REPO_ROOT!"

set "ULPF_HOME=%USERPROFILE%\.ulpf"
set "CONNECTOR_DATA_DIR=C:\ProgramData\ULPF"

:: -------------------- Confirmation --------------------
cls
echo.
echo   ============================================================
echo.
echo             U L P F   -   C L E A N U P
echo.
echo   ============================================================
echo.
echo     This will remove EVERYTHING related to a ULPF install:
echo.
echo       - Docker containers, volumes, images for this project
echo       - The ULPF connector scheduled task
echo       - C:\ProgramData\ULPF             (connector runtime)
echo       - %USERPROFILE%\.ulpf             (install logs + markers)
echo       - .env and .env.bak.*             (secrets)
echo       - backend\venv                    (Python env)
echo       - backend\*.db                    (SQLite databases)
echo       - frontend\node_modules           (npm packages)
echo       - Python caches under the repo
echo.
echo     Source code and .env.example are NOT touched.
echo.
echo   ------------------------------------------------------------
echo        Type YES to continue, anything else to cancel:
echo   ------------------------------------------------------------
echo.
set /p "CONFIRM=          > "
if /i not "!CONFIRM!"=="YES" (
    echo.
    echo          Cancelled.
    timeout /t 2 /nobreak >nul
    exit /b 0
)

echo.
echo   Starting cleanup...
echo.

:: ============================================================
:: 1. Docker
:: ============================================================
call :say "Stopping Docker stack"
docker compose down --remove-orphans >nul 2>&1
call :say "  done"

call :say "Removing ULPF Docker volumes"
call :remove_docker_volumes
call :say "  done"

call :say "Removing ULPF Docker images"
call :remove_docker_images
call :say "  done"

call :say "Removing ULPF Docker networks"
call :remove_docker_networks
call :say "  done"

call :say "Pruning Docker build cache"
docker builder prune -f >nul 2>&1
call :say "  done"

:: ============================================================
:: 2. Connector scheduled task
:: ============================================================
call :say "Removing connector scheduled task"
schtasks /Delete /TN "\ULPF\Connector" /F >nul 2>&1
schtasks /Delete /TN "\ULPF" /F >nul 2>&1
call :say "  done"

:: ============================================================
:: 3. Connector state directories
:: ============================================================
call :say "Removing C:\ProgramData\ULPF"
if exist "!CONNECTOR_DATA_DIR!" rmdir /s /q "!CONNECTOR_DATA_DIR!" >nul 2>&1
call :say "  done"

call :say "Removing %USERPROFILE%\.ulpf"
if exist "!ULPF_HOME!" rmdir /s /q "!ULPF_HOME!" >nul 2>&1
call :say "  done"

:: ============================================================
:: 4. .env and backups
:: ============================================================
call :say "Removing .env and .env backups"
if exist "!REPO_ROOT!\.env" del /q "!REPO_ROOT!\.env" >nul 2>&1
if exist "!REPO_ROOT!\.env.live" del /q "!REPO_ROOT!\.env.live" >nul 2>&1
for %%F in ("!REPO_ROOT!\.env.bak.*") do (
    del /q "%%F" >nul 2>&1
)
call :say "  done"

:: ============================================================
:: 5. Python venv
:: ============================================================
call :say "Removing backend\venv"
if exist "!REPO_ROOT!\backend\venv" rmdir /s /q "!REPO_ROOT!\backend\venv" >nul 2>&1
call :say "  done"

:: ============================================================
:: 6. SQLite databases
:: ============================================================
call :say "Removing SQLite databases in backend"
if exist "!REPO_ROOT!\backend" (
    del /q "!REPO_ROOT!\backend\*.db" >nul 2>&1
    del /q "!REPO_ROOT!\backend\*.sqlite" >nul 2>&1
    del /q "!REPO_ROOT!\backend\*.sqlite3" >nul 2>&1
    del /q "!REPO_ROOT!\backend\*.db-journal" >nul 2>&1
    del /q "!REPO_ROOT!\backend\*.db-wal" >nul 2>&1
    del /q "!REPO_ROOT!\backend\*.db-shm" >nul 2>&1
)
call :say "  done"

:: ============================================================
:: 7. Frontend node_modules + build artifacts
:: ============================================================
call :say "Removing frontend\node_modules"
if exist "!REPO_ROOT!\frontend\node_modules" rmdir /s /q "!REPO_ROOT!\frontend\node_modules" >nul 2>&1
call :say "  done"

call :say "Removing build artifacts and dist directories"
if exist "!REPO_ROOT!\frontend\dist" rmdir /s /q "!REPO_ROOT!\frontend\dist" >nul 2>&1
if exist "!REPO_ROOT!\frontend\.vite" rmdir /s /q "!REPO_ROOT!\frontend\.vite" >nul 2>&1
if exist "!REPO_ROOT!\dist" rmdir /s /q "!REPO_ROOT!\dist" >nul 2>&1
if exist "!REPO_ROOT!\frontend\buildlog.txt" del /q "!REPO_ROOT!\frontend\buildlog.txt" >nul 2>&1
if exist "!REPO_ROOT!\frontend\tsconfig.tsbuildinfo" del /q "!REPO_ROOT!\frontend\tsconfig.tsbuildinfo" >nul 2>&1
if exist "!REPO_ROOT!\backend\pytest_full.txt" del /q "!REPO_ROOT!\backend\pytest_full.txt" >nul 2>&1
if exist "!REPO_ROOT!\backend\pytest_out.txt" del /q "!REPO_ROOT!\backend\pytest_out.txt" >nul 2>&1
if exist "!REPO_ROOT!\backend\pytest_report.txt" del /q "!REPO_ROOT!\backend\pytest_report.txt" >nul 2>&1
call :say "  done"

:: ============================================================
:: 8. Python caches
:: ============================================================
call :say "Removing Python caches under the repo"
for /d /r "!REPO_ROOT!" %%D in (__pycache__ .pytest_cache .mypy_cache .ruff_cache) do (
    if exist "%%D" rmdir /s /q "%%D" >nul 2>&1
)
call :say "  done"

:: ============================================================
:: 9. Connector venv (if any)
:: ============================================================
call :say "Removing connector venv (if present)"
if exist "!REPO_ROOT!\scripts\ulpf-connector\venv" rmdir /s /q "!REPO_ROOT!\scripts\ulpf-connector\venv" >nul 2>&1
if exist "!REPO_ROOT!\scripts\ulpf-connector\.venv" rmdir /s /q "!REPO_ROOT!\scripts\ulpf-connector\.venv" >nul 2>&1
call :say "  done"

:: ============================================================
:: 10. Runtime logs / spool
:: ============================================================
call :say "Removing logs and spool directories at repo root"
if exist "!REPO_ROOT!\logs" rmdir /s /q "!REPO_ROOT!\logs" >nul 2>&1
if exist "!REPO_ROOT!\spool" rmdir /s /q "!REPO_ROOT!\spool" >nul 2>&1
call :say "  done"

:: ============================================================
:: Verification
:: ============================================================
echo.
echo   ------------------------------------------------------------
echo     Verification
echo   ------------------------------------------------------------
echo.

call :verify_docker_volume "ulpf_pg"
call :verify_docker_volume "ulpf_minio"
call :verify_docker_image "ulpf"
call :verify_schtasks
call :verify_path "C:\ProgramData\ULPF"
call :verify_path "!ULPF_HOME!"
call :verify_path "!REPO_ROOT!\.env"
call :verify_path "!REPO_ROOT!\backend\venv"
call :verify_glob "!REPO_ROOT!\backend\*.db"
call :verify_path "!REPO_ROOT!\frontend\node_modules"

echo.
echo   ------------------------------------------------------------
echo     ULPF cleanup complete.
echo   ------------------------------------------------------------
echo.
echo     To start fresh, run:  start_ulpf.bat
echo.
echo     Press any key to close this window.
pause >nul
exit /b 0

:: ============================================================
:: Docker removal helpers
:: (Avoid for /f with pipes in the command substitution.)
:: ============================================================

:remove_docker_volumes
for /f "usebackq tokens=*" %%V in (`docker volume ls --format "{{.Name}}" 2^>nul`) do (
    echo %%V | findstr /I "sih-main sih-test ulpf" >nul
    if not errorlevel 1 (
        docker volume rm -f "%%V" >nul 2>&1
    )
)
exit /b 0

:remove_docker_images
for /f "usebackq tokens=*" %%I in (`docker images --format "{{.Repository}}:{{.Tag}}" 2^>nul`) do (
    echo %%I | findstr /I "sih-main sih-test ulpf" >nul
    if not errorlevel 1 (
        docker rmi -f "%%I" >nul 2>&1
    )
)
exit /b 0

:remove_docker_networks
for /f "usebackq tokens=*" %%N in (`docker network ls --format "{{.Name}}" 2^>nul`) do (
    echo %%N | findstr /I "sih-main sih-test ulpf" >nul
    if not errorlevel 1 (
        docker network rm "%%N" >nul 2>&1
    )
)
exit /b 0

:: ============================================================
:: Verification helpers
:: Each helper runs its docker/fs command directly and sets a
:: FOUND flag. No pipes inside `for /f ... in (`cmd`)`.
:: ============================================================

:verify_docker_volume
set "TARGET=%~1"
set "FOUND="
for /f "usebackq tokens=*" %%V in (`docker volume ls --format "{{.Name}}" 2^>nul`) do (
    echo %%V | findstr /I /C:"!TARGET!" >nul
    if not errorlevel 1 set "FOUND=1"
)
if "!FOUND!"=="" (
    echo   [OK]   Docker volume *!TARGET!*  ^(removed^)
) else (
    echo   [!!]   Docker volume *!TARGET!*  ^(still present^)
)
exit /b 0

:verify_docker_image
set "NEEDLE=%~1"
set "FOUND="
for /f "usebackq tokens=*" %%I in (`docker images --format "{{.Repository}}" 2^>nul`) do (
    echo %%I | findstr /I /C:"!NEEDLE!" >nul
    if not errorlevel 1 set "FOUND=1"
)
if "!FOUND!"=="" (
    echo   [OK]   Docker image !NEEDLE!  ^(removed^)
) else (
    echo   [!!]   Docker image !NEEDLE!  ^(still present^)
)
exit /b 0

:verify_schtasks
schtasks /Query /TN "\ULPF\Connector" >nul 2>&1
if errorlevel 1 (
    echo   [OK]   Scheduled task ULPF\Connector  ^(removed^)
) else (
    echo   [!!]   Scheduled task ULPF\Connector  ^(still present^)
)
exit /b 0

:verify_path
set "P=%~1"
if exist "!P!" (
    echo   [!!]   !P!  ^(still present^)
) else (
    echo   [OK]   !P!  ^(removed^)
)
exit /b 0

:verify_glob
set "P=%~1"
set "FOUND="
for %%F in ("!P!") do set "FOUND=1"
if "!FOUND!"=="" (
    echo   [OK]   !P!  ^(removed^)
) else (
    echo   [!!]   !P!  ^(still present^)
)
exit /b 0

:: ============================================================
:: Helper: print a step
:: ============================================================
:say
echo   [*] %~1
exit /b 0