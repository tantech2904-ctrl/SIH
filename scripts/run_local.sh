#!/usr/bin/env bash
# ============================================================
#  ULPF - Universal Log Pre-Processing Framework
#  Local Worker (Linux & macOS)
#
#  Responsibilities:
#    1. Write .env from scripts/.env.local (SQLite, local memory)
#    2. Setup python virtual environment and backend dependencies
#    3. Bootstrap local SQLite database schema & initial seed
#    4. Install frontend npm dependencies
#    5. Start backend + frontend processes
#    6. Wait for readiness, open browser, provide interactive control console
# ============================================================

set -e

CLR_RESET="\033[0m"
CLR_CYAN="\033[1;36m"
CLR_GREEN="\033[1;32m"
CLR_YELLOW="\033[1;33m"
CLR_RED="\033[1;31m"
CLR_DIM="\033[2m"
CLR_BOLD="\033[1m"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPTS_DIR/.." && pwd)"

ULPF_HOME="$HOME/.ulpf"
mkdir -p "$ULPF_HOME"
INSTALL_LOG="$ULPF_HOME/install.log"

ENV_TEMPLATE="$SCRIPTS_DIR/.env.local"
ENV_TARGET="$REPO_ROOT/.env"

say() {
    echo -e "  [*] $1"
}

open_url() {
    local url="$1"
    if [[ "$(uname -s)" == "Darwin" ]]; then
        open "$url" 2>/dev/null || true
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" 2>/dev/null || true
    fi
}

# ------------------------------------------------------------
# 0. Python Detection
# ------------------------------------------------------------
PY_BIN=""
PY_VER=""
for candidate in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        VER_STR=$("$candidate" --version 2>&1 || true)
        case "$VER_STR" in
            *"Python 3.10"*|*"Python 3.11"*|*"Python 3.12"*)
                PY_BIN="$candidate"
                PY_VER="$VER_STR"
                break
                ;;
        esac
    fi
done

if [[ -z "$PY_BIN" ]]; then
    echo -e "${CLR_RED}  [ERROR] No supported Python (3.10, 3.11, or 3.12) found.${CLR_RESET}"
    exit 1
fi

clear 2>/dev/null || true
echo ""
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo -e "${CLR_CYAN}                U L P F   -   L O C A L   M O D E             ${CLR_RESET}"
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo ""
echo "    Python: $PY_VER ($PY_BIN)"
echo ""

# ------------------------------------------------------------
# 1. Write .env for Local
# ------------------------------------------------------------
say "Preparing .env for Local..."
if [[ ! -f "$ENV_TEMPLATE" ]]; then
    echo -e "${CLR_RED}  [ERROR] scripts/.env.local not found.${CLR_RESET}"
    exit 1
fi

if [[ -f "$ENV_TARGET" ]]; then
    TS=$(date '+%Y%m%d_%H%M%S')
    mv "$ENV_TARGET" "${ENV_TARGET}.bak.${TS}" 2>/dev/null || true
    echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Backed up old .env to .env.bak.${TS}"
fi

cp "$ENV_TEMPLATE" "$ENV_TARGET"
echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} .env written from scripts/.env.local"

# ------------------------------------------------------------
# 2. venv + deps
# ------------------------------------------------------------
cd "$REPO_ROOT"
VENV_DIR="$REPO_ROOT/backend/venv"
VENV_PY="$VENV_DIR/bin/python"

if [[ ! -f "$VENV_PY" ]]; then
    say "Creating Python venv with $PY_BIN..."
    rm -rf "$VENV_DIR" 2>/dev/null || true
    "$PY_BIN" -m venv "$VENV_DIR"
    if [[ ! -f "$VENV_PY" ]]; then
        echo -e "${CLR_RED}  [ERROR] venv creation failed.${CLR_RESET}"
        exit 1
    fi
    echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Virtual environment created."
fi

say "Installing backend dependencies..."
"$VENV_PY" -m pip install --quiet --disable-pip-version-check --no-cache-dir -r "$REPO_ROOT/backend/requirements.txt" >> "$INSTALL_LOG" 2>&1
echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Backend dependencies verified."

if [[ -f "$REPO_ROOT/backend/requirements-optional.txt" ]]; then
    "$VENV_PY" -m pip install --quiet --disable-pip-version-check --no-cache-dir -r "$REPO_ROOT/backend/requirements-optional.txt" >> "$INSTALL_LOG" 2>&1 || true
    echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Optional dependencies processed."
fi

# ------------------------------------------------------------
# 3. Bootstrap SQLite schema + seed
# ------------------------------------------------------------
say "Bootstrapping local SQLite database..."
BOOTSTRAP_SCRIPT=$(cat << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "backend"))
from app.db.base import Base
from app.db.session import engine
Base.metadata.create_all(bind=engine)
from app.db.init_db import init_db
init_db()
print("BOOTSTRAP_OK")
EOF
)

cd "$REPO_ROOT"
python_out=$(python3 -c "$BOOTSTRAP_SCRIPT" 2>&1 || true)
echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Database schema and admin seed initialized."

# ------------------------------------------------------------
# 4. Frontend dependencies
# ------------------------------------------------------------
if [[ ! -d "$REPO_ROOT/frontend/node_modules" ]]; then
    say "Installing frontend dependencies..."
    (cd "$REPO_ROOT/frontend" && npm install --silent >> "$INSTALL_LOG" 2>&1)
    echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Frontend dependencies installed."
fi

# ------------------------------------------------------------
# 5. Spawn backend + frontend background processes
# ------------------------------------------------------------
BACKEND_LOG="$ULPF_HOME/backend.log"
FRONTEND_LOG="$ULPF_HOME/frontend.log"

say "Starting backend (port 8000)..."
(cd "$REPO_ROOT/backend" && "$VENV_PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$BACKEND_LOG" 2>&1) &
BACKEND_PID=$!

say "Starting frontend dev server (port 5173)..."
(cd "$REPO_ROOT/frontend" && npm run dev > "$FRONTEND_LOG" 2>&1) &
FRONTEND_PID=$!

cleanup_procs() {
    echo ""
    echo -e "${CLR_YELLOW}  Stopping local processes...${CLR_RESET}"
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    # Kill any child uvicorn or vite processes
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    echo -e "${CLR_GREEN}  ULPF stopped. Goodbye!${CLR_RESET}"
}
trap cleanup_procs EXIT INT TERM

# ------------------------------------------------------------
# 6. Wait for readiness
# ------------------------------------------------------------
say "Waiting for frontend and backend to start..."
TICKS=0
MAX=150

while [[ $TICKS -lt $MAX ]]; do
    TICKS=$((TICKS + 1))
    
    FRONTEND_OK=0
    BACKEND_OK=0

    if curl -s -m 2 http://localhost:5173 >/dev/null 2>&1; then
        FRONTEND_OK=1
    fi

    if curl -s -m 2 http://localhost:8000/api/v1/health/ready >/dev/null 2>&1; then
        BACKEND_OK=1
    fi

    if [[ $FRONTEND_OK -eq 1 && $BACKEND_OK -eq 1 ]]; then
        break
    fi

    PCT=$((TICKS * 100 / MAX))
    [[ $PCT -gt 99 ]] && PCT=99
    FILL=$((PCT / 2))
    SP=$((50 - FILL))
    
    BAR=$(printf '%*s' "$FILL" | tr ' ' '#')
    DOTS=$(printf '%*s' "$SP" | tr ' ' '.')

    echo -ne "\r         [${BAR}${DOTS}] ${PCT}% (Waiting for servers...)"
    sleep 2
done

echo ""
if [[ $TICKS -ge $MAX ]]; then
    echo -e "${CLR_RED}  [!!] ULPF did not become ready in time.${CLR_RESET}"
    echo "       Check $BACKEND_LOG and $FRONTEND_LOG for details."
    exit 1
fi

echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Frontend & Backend live."

# ------------------------------------------------------------
# 7. Control console
# ------------------------------------------------------------
draw_console() {
    clear 2>/dev/null || true
    echo ""
    echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
    echo -e "${CLR_CYAN}                 U L P F   L O C A L   R U N N I N G          ${CLR_RESET}"
    echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
    echo ""
    echo "    Frontend:  http://localhost:5173"
    echo "    API:       http://localhost:8000"
    echo "    API Docs:  http://localhost:8000/docs"
    echo ""
    echo "    Database:  backend/ulpf_local.db  (SQLite)"
    echo "    Redis:     memory://              (in-process)"
    echo "    Storage:   backend/data/raw/      (local files)"
    echo ""
    echo "    Login:     admin@ulpf.local / ChangeMe_Admin123!"
    echo ""
    echo "  ------------------------------------------------------------"
    echo "    Workspaces:"
    echo "      1. SOC Command Center       4. Pipeline & Schema Normalization"
    echo "      2. Live Telemetry & Streams 5. Threat Detection & MITRE ATT&CK"
    echo "      3. Discovery & ML Export    6. Forensic Evidence & Audit"
    echo "  ------------------------------------------------------------"
    echo "    Commands:"
    echo "      s   status       l   logs (backend)  o   open browser"
    echo "      h   help         r   restart servers b   reinstall dependencies"
    echo "      c   clear        q   quit & stop"
    echo ""
}

echo "         Opening browser..."
open_url "http://localhost:5173"

draw_console

while true; do
    echo -ne "${CLR_BOLD}ulpf-local> ${CLR_RESET}"
    read -r -n 1 cmd || true
    echo ""

    case "$cmd" in
        s|S)
            echo ""
            echo "  Processes:"
            echo "    Backend PID:  $BACKEND_PID ($(kill -0 "$BACKEND_PID" 2>/dev/null && echo "RUNNING" || echo "STOPPED"))"
            echo "    Frontend PID: $FRONTEND_PID ($(kill -0 "$FRONTEND_PID" 2>/dev/null && echo "RUNNING" || echo "STOPPED"))"
            echo ""
            ;;
        l|L)
            clear 2>/dev/null || true
            echo ""
            echo "  ----- Last 30 lines: backend -----"
            tail -n 30 "$BACKEND_LOG" 2>/dev/null || echo "No logs yet."
            echo ""
            echo -n "  Press Enter to continue..."
            read -r
            draw_console
            ;;
        o|O)
            open_url "http://localhost:5173"
            ;;
        h|H)
            clear 2>/dev/null || true
            echo ""
            echo "  s - status   l - logs   o - open browser"
            echo "  h - help     r - restart servers"
            echo "  b - reinstall deps   c - clear   q - quit"
            echo ""
            echo -n "  Press Enter to continue..."
            read -r
            draw_console
            ;;
        r|R)
            say "Restarting backend and frontend..."
            kill "$BACKEND_PID" 2>/dev/null || true
            kill "$FRONTEND_PID" 2>/dev/null || true
            pkill -f "uvicorn app.main:app" 2>/dev/null || true
            pkill -f "vite" 2>/dev/null || true
            sleep 1
            (cd "$REPO_ROOT/backend" && "$VENV_PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$BACKEND_LOG" 2>&1) &
            BACKEND_PID=$!
            (cd "$REPO_ROOT/frontend" && npm run dev > "$FRONTEND_LOG" 2>&1) &
            FRONTEND_PID=$!
            sleep 2
            draw_console
            ;;
        b|B)
            echo ""
            echo -n "  Reinstall Python + Node dependencies? [y/N]: "
            read -r rbok
            if [[ "$rbok" =~ ^[Yy]$ ]]; then
                say "Reinstalling backend deps..."
                "$VENV_PY" -m pip install -r "$REPO_ROOT/backend/requirements.txt" >> "$INSTALL_LOG" 2>&1
                say "Reinstalling frontend deps..."
                (cd "$REPO_ROOT/frontend" && npm install >> "$INSTALL_LOG" 2>&1)
                draw_console
            fi
            ;;
        c|C)
            draw_console
            ;;
        q|Q)
            exit 0
            ;;
        *)
            ;;
    esac
done
