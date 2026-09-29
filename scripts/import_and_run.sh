#!/usr/bin/env bash
# ============================================================
#  ULPF SIEM - Smart India Hackathon Demo Launcher (Linux & macOS)
#  Universal Log Pre-Processing Framework
# ============================================================

set -e

CLR_RESET="\033[0m"
CLR_CYAN="\033[1;36m"
CLR_GREEN="\033[1;32m"
CLR_YELLOW="\033[1;33m"
CLR_RED="\033[1;31m"
CLR_BOLD="\033[1m"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPTS_DIR/.." && pwd)"

open_url() {
    local url="$1"
    if [[ "$(uname -s)" == "Darwin" ]]; then
        open "$url" 2>/dev/null || true
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" 2>/dev/null || true
    fi
}

clear 2>/dev/null || true
echo ""
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo -e "${CLR_CYAN}                    U L P F   S I E M                         ${CLR_RESET}"
echo -e "${CLR_CYAN}        Universal Log Pre-Processing Framework                ${CLR_RESET}"
echo -e "${CLR_CYAN}        Smart India Hackathon - Live Demonstration            ${CLR_RESET}"
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo ""

# 1. Docker check
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${CLR_RED}  [ERROR] Docker not found on this machine.${CLR_RESET}"
    echo "          Please install Docker / Docker Desktop before running this script."
    exit 1
fi

# 2. Locate image archive
IMAGES=""
if [[ -f "$SCRIPTS_DIR/ulpf-sih-demo-images.tar" ]]; then
    IMAGES="$SCRIPTS_DIR/ulpf-sih-demo-images.tar"
elif [[ -f "$REPO_ROOT/ulpf-sih-demo-images.tar" ]]; then
    IMAGES="$REPO_ROOT/ulpf-sih-demo-images.tar"
elif [[ -f "$REPO_ROOT/dist/ulpf-sih-demo-images.tar" ]]; then
    IMAGES="$REPO_ROOT/dist/ulpf-sih-demo-images.tar"
fi

# 3. Load images if archive is present and not yet loaded
if docker image inspect ulpf-backend:demo >/dev/null 2>&1; then
    echo -e "  ${CLR_GREEN}[OK]${CLR_RESET} Images already loaded - skipping import (fast start)."
    echo ""
elif [[ -n "$IMAGES" && -f "$IMAGES" ]]; then
    echo "  [*] Loading ULPF images from archive ($IMAGES)..."
    echo "      This takes 2-4 minutes on first run. Please wait."
    echo ""
    docker load -i "$IMAGES"
    echo -e "  ${CLR_GREEN}[OK]${CLR_RESET} Images loaded successfully."
    echo ""
else
    echo "  [*] Image archive not found; building or pulling stack via docker compose..."
fi

# 4. Navigate to project root & set .env
cd "$REPO_ROOT"
if [[ -f "scripts/.env.docker" ]]; then
    cp -f "scripts/.env.docker" ".env"
    echo -e "  ${CLR_GREEN}[OK]${CLR_RESET} Environment configured for Docker mode."
fi

# 5. Start stack
echo "  [*] Starting ULPF SIEM..."
docker compose up -d --remove-orphans
echo ""

# 6. Wait for readiness
echo "  [*] Waiting for services to become responsive..."
TICKS=0
MAX=90

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
    echo -ne "\r      Startup Progress: ${PCT}%    "
    sleep 3
done

echo ""
if [[ $TICKS -ge $MAX ]]; then
    echo -e "${CLR_YELLOW}  [!!] Services did not report ready within 4.5 minutes.${CLR_RESET}"
    docker compose ps
    exit 1
fi

open_url "http://localhost:5173"

draw_demo_console() {
    clear 2>/dev/null || true
    echo ""
    echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
    echo -e "${CLR_CYAN}                  ULPF SIEM IS RUNNING!                       ${CLR_RESET}"
    echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
    echo ""
    echo "    Open in browser:  http://localhost:5173"
    echo "    API Docs:         http://localhost:8000/docs"
    echo "    Storage UI:       http://localhost:9001  (ulpfadmin / ulpfadminsecret)"
    echo ""
    echo "  ============================================================"
    echo "    Demo Credentials:"
    echo "      [Admin]    admin@ulpf.local     ChangeMe_Admin123!   <-- Start here"
    echo "      [Analyst]  analyst@ulpf.local   ChangeMe_Analyst123!"
    echo "      [Auditor]  auditor@ulpf.local   ChangeMe_Auditor123!"
    echo ""
    echo "    Platform Capabilities:"
    echo "      - 6 Unified Workspaces: Command Center, Telemetry, Discovery,"
    echo "        Pipeline Normalization, MITRE ATT&CK Detection, Forensic Evidence"
    echo "      - ML Training Dataset Export (JSONL / CSV / JSON up to 10k records)"
    echo "      - Plug-and-Play Parsers, Field Mappings, and Quarantine Replay"
    echo ""
    echo "    Quick Demo Steps:"
    echo "      1. Log in as Admin"
    echo "      2. Click [Site Tour] in top bar for interactive guided walkthrough"
    echo "      3. Click [Run Demo] on Dashboard to generate 11 attack scenarios live"
    echo "      4. Inspect Live Stream SSE telemetry and Event Explorer datasets"
    echo "  ============================================================"
    echo ""
    echo "    Commands (press key):"
    echo "      s   status          l   backend logs"
    echo "      a   all logs        o   open browser"
    echo "      q   quit & stop ULPF"
    echo ""
}

draw_demo_console

while true; do
    echo -ne "${CLR_BOLD}ulpf-demo> ${CLR_RESET}"
    read -r -n 1 cmd || true
    echo ""

    case "$cmd" in
        s|S)
            echo ""
            docker compose ps
            echo ""
            ;;
        l|L)
            echo ""
            docker compose logs --tail=25 backend
            echo ""
            ;;
        a|A)
            echo ""
            docker compose logs --tail=25
            echo ""
            ;;
        o|O)
            open_url "http://localhost:5173"
            ;;
        q|Q)
            echo ""
            echo "  Stopping ULPF SIEM..."
            docker compose down
            echo -e "${CLR_GREEN}  Done. Goodbye!${CLR_RESET}"
            exit 0
            ;;
        *)
            ;;
    esac
done
