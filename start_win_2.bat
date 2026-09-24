@echo off
setlocal EnableDelayedExpansion
title ULPF - Universal Log Pre-Processing Framework
color 0B

cd /d "%~dp0"

cls
echo.
echo  ============================================================
echo.
echo        U L P F   -   UNIVERSAL LOG PRE-PROCESSING
echo                    FRAMEWORK
echo.
echo        MANUAL STARTUP ^| LOCAL DEVELOPMENT
echo.
echo  ============================================================
echo.
echo        Initializing ULPF services...
echo.

:: ============================================================
:: CHECK PYTHON
:: ============================================================

echo  [1/6]  Checking Python...

python --version >nul 2>&1

if errorlevel 1 (
    color 0C
    echo.
    echo  ============================================================
    echo   ERROR
    echo  ============================================================
    echo.
    echo   Python was not found.
    echo   Please install Python 3.11+ and try again.
    echo.
    pause
    exit /b 1
)

echo          [OK] Python found.

:: ============================================================
:: CHECK NODE
:: ============================================================

echo.
echo  [2/6]  Checking Node.js...

node --version >nul 2>&1

if errorlevel 1 (
    color 0C
    echo.
    echo  ============================================================
    echo   ERROR
    echo  ============================================================
    echo.
    echo   Node.js was not found.
    echo   Please install Node.js and try again.
    echo.
    pause
    exit /b 1
)

echo          [OK] Node.js found.

:: ============================================================
:: BACKEND VENV
:: ============================================================

echo.
echo  [3/6]  Preparing backend...

cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
    echo          Creating Python virtual environment...
    python -m venv venv

    if errorlevel 1 (
        color 0C
        echo.
        echo  ============================================================
        echo   ERROR
        echo  ============================================================
        echo.
        echo   Failed to create Python virtual environment.
        echo.
        pause
        exit /b 1
    )

    echo          [OK] Virtual environment created.
)

:: ============================================================
:: CREATE LOCAL ENV
:: ============================================================

if not exist ".env" (
    if exist ".env.example" (
        echo          Creating local .env from .env.example...
        copy /Y ".env.example" ".env" >nul

        if errorlevel 1 (
            color 0C
            echo.
            echo  ============================================================
            echo   ERROR
            echo  ============================================================
            echo.
            echo   Failed to create local .env file.
            echo.
            pause
            exit /b 1
        )

        echo          [OK] Local .env created.
    ) else (
        color 0E
        echo          WARNING: .env.example was not found.
        echo          Continuing without creating .env...
        color 0B
    )
) else (
    echo          [OK] Local .env already exists.
)

echo.
echo          Installing backend dependencies...
venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-cache-dir --default-timeout=100 --retries=8 -r requirements.txt

if errorlevel 1 (
    color 0C
    echo.
    echo  ============================================================
    echo   ERROR
    echo  ============================================================
    echo.
    echo   Backend dependency installation failed.
    echo.
    pause
    exit /b 1
)

echo          [OK] Backend ready.

:: ============================================================
:: START BACKEND
:: ============================================================

echo.
echo  [4/6]  Starting FastAPI backend...

start "ULPF Backend" cmd /k "cd /d ""%~dp0backend"" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo          [OK] Backend starting...

:: ============================================================
:: FRONTEND
:: ============================================================

echo.
echo  [5/6]  Preparing frontend...

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo          Installing frontend dependencies...
    call npm install

    if errorlevel 1 (
        color 0C
        echo.
        echo  ============================================================
        echo   ERROR
        echo  ============================================================
        echo.
        echo   Frontend dependency installation failed.
        echo.
        pause
        exit /b 1
    )
)

echo          Building frontend...
call npm run build

if errorlevel 1 (
    color 0C
    echo.
    echo  ============================================================
    echo   ERROR
    echo  ============================================================
    echo.
    echo   Frontend build failed.
    echo.
    pause
    exit /b 1
)

echo          [OK] Frontend ready.

:: ============================================================
:: START FRONTEND
:: ============================================================

echo.
echo  [6/6]  Starting frontend...

start "ULPF Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

:: ============================================================
:: WAIT FOR FRONTEND
:: ============================================================

echo.
echo  ============================================================
echo              STARTING ULPF SERVICES
echo  ============================================================
echo.
echo          Backend  : FastAPI
echo          Frontend : Vite
echo.
echo          Waiting for frontend to become available...
echo.

set /a COUNT=0

:WAIT

set /a COUNT+=1

if !COUNT! GTR 30 (
    color 0E
    echo.
    echo  ============================================================
    echo   ULPF IS TAKING LONGER THAN EXPECTED
    echo  ============================================================
    echo.
    echo   Try opening:
    echo   http://localhost:5173
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (
    set /a PERCENT=!COUNT!*100/30

    cls
    echo.
    echo  ============================================================
    echo                    STARTING ULPF
    echo  ============================================================
    echo.
    echo          Progress: [!PERCENT!%%]
    echo.
    echo          [*] Python environment
    echo          [*] FastAPI backend
    echo          [*] Node.js
    echo          [*] Vite frontend
    echo.
    echo          Waiting for frontend...
    echo.
    timeout /t 2 /nobreak >nul

    goto WAIT
)

:: ============================================================
:: SUCCESS
:: ============================================================

color 0A
cls

echo.
echo  ============================================================
echo.
echo                 U L P F   I S   R E A D Y
echo.
echo        UNIVERSAL LOG PRE-PROCESSING FRAMEWORK
echo.
echo  ============================================================
echo.
echo          [OK] Python environment
echo          [OK] Backend
echo          [OK] Frontend
echo          [OK] Local configuration
echo.
echo  ------------------------------------------------------------
echo.
echo          FRONTEND
echo          http://localhost:5173
echo.
echo          API
echo          http://localhost:8000
echo.
echo          API HEALTH
echo          http://localhost:8000/api/v1/health
echo.
echo          API DOCS
echo          http://localhost:8000/docs
echo.
echo  ------------------------------------------------------------
echo.
echo          Opening ULPF...
echo.

timeout /t 2 /nobreak >nul

start "" "http://localhost:5173"

echo.
echo          ULPF is running.
echo.
echo          Backend and frontend are running in
echo          separate terminal windows.
echo.
echo          Close those windows to stop ULPF.
echo.
echo  ============================================================
echo.
pause