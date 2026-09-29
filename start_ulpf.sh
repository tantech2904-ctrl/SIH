#!/usr/bin/env bash
# ============================================================
#  ULPF - Universal Log Pre-Processing Framework
#  Linux Control & Setup Script
#
#  Features:
#    1. Interactive / CLI mode selection (Docker vs Local)
#    2. Automatic Docker / Python environment verification
#    3. Initial .env configuration initialization
#    4. Dispatches to scripts/run_docker.sh or scripts/run_local.sh
#    (Host connector setup omitted on Linux per configuration)
# ============================================================

set -e

# ANSI Colors
CLR_RESET="\033[0m"
CLR_CYAN="\033[1;36m"
CLR_GREEN="\033[1;32m"
CLR_YELLOW="\033[1;33m"
CLR_RED="\033[1;31m"
CLR_DIM="\033[2m"
CLR_BOLD="\033[1m"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

ULPF_HOME="$HOME/.ulpf"
mkdir -p "$ULPF_HOME"
INSTALL_LOG="$ULPF_HOME/install.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$INSTALL_LOG"
}

draw_header() {
    clear 2>/dev/null || true
    echo -e "${CLR_CYAN}"
    echo "  ============================================================"
    echo "              U L P F   -   S E T U P  ( L I N U X )"
    echo "       Universal Log Pre-Processing & Telemetry Framework"
    echo "  ============================================================"
    echo -e "${CLR_RESET}"
}

draw_header
echo "      This will prepare and start ULPF on your computer."
echo ""
log "===== ULPF setup starting on Linux ====="
log "Repo root: $REPO_ROOT"

# Check Docker
check_docker() {
    if command -v docker >/dev/null 2>&1; then
        DOCKER_VER=$(docker --version 2>/dev/null || echo "Docker installed")
        echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} $DOCKER_VER"
        return 0
    else
        return 1
    fi
}

# Check Python
check_python() {
    PY_BIN=""
    PY_VER=""
    for candidate in python3.12 python3.11 python3.10 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            VER_STR=$("$candidate" --version 2>&1 || true)
            case "$VER_STR" in
                *"Python 3.10"*|*"Python 3.11"*|*"Python 3.12"*)
                    PY_BIN="$candidate"
                    PY_VER="$VER_STR"
                    return 0
                    ;;
            esac
        fi
    done
    return 1
}

# ============================================================
# STEP 1 - MODE SELECTION
# ============================================================
MODE=""
ARG1="${1:-}"

if [[ "$ARG1" == "1" || "$ARG1" == "docker" || "$ARG1" == "--docker" ]]; then
    MODE="docker"
elif [[ "$ARG1" == "2" || "$ARG1" == "local" || "$ARG1" == "--local" ]]; then
    MODE="local"
fi

if [[ -z "$MODE" ]]; then
    echo "       How would you like to run ULPF?"
    echo ""
    echo "  ------------------------------------------------------------"
    echo "       [1]  Docker      (recommended - full production stack)"
    echo "       [2]  Local       (uses host Python + Node.js directly)"
    echo "       [3]  Exit"
    echo "  ------------------------------------------------------------"
    echo ""
    echo "       Starting in Docker mode automatically in 5 seconds..."
    echo -n "       Enter choice [1/2/3] (default 1): "

    if read -t 5 user_choice; then
        case "$user_choice" in
            2) MODE="local" ;;
            3) echo ""; echo "       Exiting."; exit 0 ;;
            *) MODE="docker" ;;
        esac
    else
        echo "1"
        MODE="docker"
    fi
fi

if [[ "$MODE" == "docker" ]]; then
    log "Mode: docker"
    if ! check_docker; then
        echo -e "${CLR_YELLOW}         [!!] Docker is not available in PATH.${CLR_RESET}"
        echo "              Please install Docker and Docker Compose before continuing."
        exit 1
    fi
elif [[ "$MODE" == "local" ]]; then
    log "Mode: local"
    if check_python; then
        echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} $PY_VER ($PY_BIN)"
    else
        echo -e "${CLR_RED}         [!!] Local mode requires Python 3.10, 3.11, or 3.12.${CLR_RESET}"
        echo "              Please install Python 3.10+ (e.g. apt install python3 python3-venv)"
        exit 1
    fi
fi

log "Mode locked: $MODE"

# Ensure .env exists
if [[ ! -f "$REPO_ROOT/.env" ]]; then
    if [[ -f "$REPO_ROOT/.env.example" ]]; then
        cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
        echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Created initial .env configuration."
    fi
fi

# ============================================================
# STEP 2 - CONNECTOR SERVICE
# Note: Host connector setup intentionally omitted for Linux server host
# ============================================================
echo ""
echo -e "  [1/2] ${CLR_BOLD}Host log connector...${CLR_RESET}"
echo -e "         ${CLR_DIM}[--] Connector auto-setup skipped on Linux server host.${CLR_RESET}"
echo -e "         ${CLR_DIM}     (Remote endpoints connect via Web UI / download options)${CLR_RESET}"
log "Connector setup skipped on Linux host."

# ============================================================
# STEP 3 - DISPATCH TO WORKER
# ============================================================
echo ""
echo -e "  [2/2] ${CLR_BOLD}Handing off to $MODE worker...${CLR_RESET}"
echo ""

if [[ "$MODE" == "docker" ]]; then
    if [[ ! -f "$REPO_ROOT/scripts/run_docker.sh" ]]; then
        echo -e "${CLR_RED}         ERROR: scripts/run_docker.sh not found.${CLR_RESET}"
        exit 1
    fi
    chmod +x "$REPO_ROOT/scripts/run_docker.sh" 2>/dev/null || true
    log "Dispatching to run_docker.sh"
    exec "$REPO_ROOT/scripts/run_docker.sh"
else
    if [[ ! -f "$REPO_ROOT/scripts/run_local.sh" ]]; then
        echo -e "${CLR_RED}         ERROR: scripts/run_local.sh not found.${CLR_RESET}"
        exit 1
    fi
    chmod +x "$REPO_ROOT/scripts/run_local.sh" 2>/dev/null || true
    log "Dispatching to run_local.sh"
    exec "$REPO_ROOT/scripts/run_local.sh"
fi
