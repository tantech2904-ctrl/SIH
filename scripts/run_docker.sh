#!/usr/bin/env bash
# ============================================================
#  ULPF - Universal Log Pre-Processing Framework
#  Docker Worker (Linux & macOS)
#
#  Responsibilities:
#    1. Write .env from scripts/.env.docker (with backup)
#    2. docker compose up -d --remove-orphans
#    3. Wait for services to be healthy with progress indicator
#    4. Open browser, enter interactive control console
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

ENV_TEMPLATE="$SCRIPTS_DIR/.env.docker"
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

# ============================================================
# 1. Write .env for Docker
# ============================================================
clear 2>/dev/null || true
echo ""
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo -e "${CLR_CYAN}               U L P F   -   D O C K E R   M O D E            ${CLR_RESET}"
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo ""

say "Preparing .env for Docker..."
if [[ ! -f "$ENV_TEMPLATE" ]]; then
    echo -e "${CLR_RED}  [ERROR] scripts/.env.docker template not found.${CLR_RESET}"
    exit 1
fi

if [[ -f "$ENV_TARGET" ]]; then
    TS=$(date '+%Y%m%d_%H%M%S')
    mv "$ENV_TARGET" "${ENV_TARGET}.bak.${TS}" 2>/dev/null || true
    echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Backed up old .env to .env.bak.${TS}"
fi

cp "$ENV_TEMPLATE" "$ENV_TARGET"
echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} .env written from scripts/.env.docker"

# ============================================================
# 2. Start Docker stack
# ============================================================
cd "$REPO_ROOT"
say "Running docker compose up -d --remove-orphans..."

if ! docker compose up -d --remove-orphans; then
    echo ""
    echo -e "${CLR_RED}  [!!] docker compose up failed.${CLR_RESET}"
    echo "       Common causes:"
    echo "         - Docker daemon is not running"
    echo "         - Ports 5173, 8000, 5432, 6379, 9000 already bound"
    echo "         - Insufficient memory / disk space"
    exit 1
fi

echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} Docker containers initiated."

# ============================================================
# 3. Wait for readiness
# ============================================================
say "Waiting for services to become healthy..."
TICKS=0
MAX=150

while [[ $TICKS -lt $MAX ]]; do
    TICKS=$((TICKS + 1))
    
    # Check frontend and backend readiness
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

    echo -ne "\r         [${BAR}${DOTS}] ${PCT}% (Waiting for containers...)"
    sleep 2
done

echo ""
if [[ $TICKS -ge $MAX ]]; then
    echo -e "${CLR_YELLOW}  [!!] Services did not report ready within 300s.${CLR_RESET}"
    docker compose ps
    exit 1
fi

echo -e "         ${CLR_GREEN}[OK]${CLR_RESET} All ULPF services verified healthy."

# ============================================================
# 4. Control Console
# ============================================================
draw_console() {
    clear 2>/dev/null || true
    echo ""
    echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
    echo -e "${CLR_CYAN}               U L P F   D O C K E R   R U N N I N G          ${CLR_RESET}"
    echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
    echo ""
    echo "    Frontend:    http://localhost:5173"
    echo "    API Docs:    http://localhost:8000/docs"
    echo "    Storage UI:  http://localhost:9001  (ulpfadmin / ulpfadminsecret)"
    echo ""
    echo "    Login:       admin@ulpf.local / ChangeMe_Admin123!"
    echo ""
    echo "  ------------------------------------------------------------"
    echo "    Workspaces:"
    echo "      1. SOC Command Center       4. Pipeline & Schema Normalization"
    echo "      2. Live Telemetry & Streams 5. Threat Detection & MITRE ATT&CK"
    echo "      3. Discovery & ML Export    6. Forensic Evidence & Audit"
    echo "  ------------------------------------------------------------"
    echo "    Commands:"
    echo "      s   status       l   logs          o   open browser"
    echo "      h   help         r   restart       b   rebuild images"
    echo "      c   clear        q   quit & stop"
    echo ""
}

echo "         Opening browser..."
open_url "http://localhost:5173"

draw_console

while true; do
    echo -ne "${CLR_BOLD}ulpf-docker> ${CLR_RESET}"
    read -r -n 1 cmd || true
    echo ""
    
    case "$cmd" in
        s|S)
            echo ""
            docker compose ps
            echo ""
            ;;
        l|L)
            clear 2>/dev/null || true
            echo ""
            echo "  ----- Last 30 lines: backend -----"
            docker compose logs --tail=30 backend
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
            echo "  h - help     r - restart stack"
            echo "  b - rebuild  c - clear  q - quit & stop"
            echo ""
            echo -n "  Press Enter to continue..."
            read -r
            draw_console
            ;;
        r|R)
            echo "  Restarting stack..."
            docker compose restart
            sleep 2
            draw_console
            ;;
        b|B)
            echo ""
            echo -n "  Rebuild images from scratch? [y/N]: "
            read -r rbok
            if [[ "$rbok" =~ ^[Yy]$ ]]; then
                docker compose build --no-cache backend worker frontend
                docker compose up -d --remove-orphans
                sleep 2
                draw_console
            fi
            ;;
        c|C)
            draw_console
            ;;
        q|Q)
            echo ""
            echo -e "${CLR_YELLOW}  Stopping Docker stack...${CLR_RESET}"
            docker compose down
            echo -e "${CLR_GREEN}  ULPF stopped successfully. Goodbye!${CLR_RESET}"
            exit 0
            ;;
        *)
            ;;
    esac
done
