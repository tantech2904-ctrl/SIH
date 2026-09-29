@echo off
setlocal EnableDelayedExpansion
title ULPF - Export Demo Bundle
color 0B

set "REPO=%~dp0.."
set "OUT=%REPO%\dist"

echo.
echo   ============================================================
echo     ULPF SIH Demo: Export Script
echo     Builds all Docker images and saves to dist\
echo   ============================================================
echo.

:: Create output dir
if not exist "!OUT!" mkdir "!OUT!"

:: Build images fresh
echo   [1/3] Building Docker images (may take 10-20 minutes)...
cd /d "!REPO!"
docker compose build --no-cache
if errorlevel 1 (
    color 0C
    echo.
    echo   [ERROR] Docker build failed.
    echo           Make sure Docker Desktop is running and try again.
    echo.
    pause
    exit /b 1
)
echo   [OK] All images built successfully.

:: Save to archive
echo.
echo   [2/3] Saving images to archive (approx 2-3 GB, ~5-8 minutes)...
echo.
docker save ^
    ulpf-backend:demo ^
    ulpf-worker:demo ^
    ulpf-frontend:demo ^
    postgres:16-alpine ^
    redis:7-alpine ^
    ghcr.io/wrkode/openbucket:latest ^
    -o "!OUT!\ulpf-sih-demo-images.tar"

if errorlevel 1 (
    color 0C
    echo.
    echo   [ERROR] docker save failed.
    echo           Ensure all images built correctly: docker images
    echo.
    pause
    exit /b 1
)
echo   [OK] Archive saved: dist\ulpf-sih-demo-images.tar

:: Copy project files (exclude heavy build artifacts)
echo.
echo   [3/3] Copying project files to dist\ulpf-demo\...
if exist "!OUT!\ulpf-demo" rmdir /s /q "!OUT!\ulpf-demo" >nul
robocopy "!REPO!" "!OUT!\ulpf-demo" /E ^
    /XD node_modules .git venv .venv dist __pycache__ .pytest_cache .mypy_cache .ruff_cache .vite ^
    /XF "*.pyc" "*.tar" "*.log" "*.bak.*" "tsconfig.tsbuildinfo" "*.db" "*.sqlite*" "buildlog.txt" "pytest_*.txt" ^
    /NFL /NDL /NJH /NJS /nc /ns /np >nul

:: Copy the image archive into ulpf-demo for a single folder handoff
echo   Copying image archive into ulpf-demo\ folder...
copy /Y "!OUT!\ulpf-sih-demo-images.tar" "!OUT!\ulpf-demo\ulpf-sih-demo-images.tar" >nul

echo.
echo   ============================================================
echo     DONE!
echo.
echo     Hand judges the entire dist\ulpf-demo\ folder:
echo.
echo       dist\ulpf-demo\ulpf-sih-demo-images.tar   (~2.5 GB)
echo       dist\ulpf-demo\scripts\import_and_run.bat  (entry point)
echo       dist\ulpf-demo\README_DEMO.md              (judge guide)
echo.
echo     The judge runs: scripts\import_and_run.bat
echo     (or double-click it from Windows Explorer)
echo   ============================================================
echo.
pause
