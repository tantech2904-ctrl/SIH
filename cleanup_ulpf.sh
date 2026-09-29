#!/usr/bin/env bash
# ============================================================
#  ULPF - Universal Log Pre-Processing Framework
#  Full Cleanup & Reset Script (Linux & macOS)
#
#  Removes:
#    - Docker containers, volumes, networks, and images for ULPF
#    - Connector runtime state (~/.ulpf, ~/.ulpf-connector, /tmp/ulpf*)
#    - .env and .env.bak.* (keeps .env.example)
#    - backend/venv, backend/*.db, backend/data/raw
#    - frontend/node_modules, frontend/dist
#    - Python caches (__pycache__, .pytest_cache)
#
#  Does NOT touch:
#    - Source code, git history, or documentation
#    - .env.example, scripts/.env.docker, scripts/.env.local
# ============================================================

set -e

CLR_RESET="\033[0m"
CLR_CYAN="\033[1;36m"
CLR_GREEN="\033[1;32m"
CLR_YELLOW="\033[1;33m"
CLR_RED="\033[1;31m"
CLR_DIM="\033[2m"
CLR_BOLD="\033[1m"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

say() {
    echo -e "  [*] $1"
}

clear 2>/dev/null || true
echo ""
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo -e "${CLR_CYAN}                 U L P F   -   C L E A N U P                  ${CLR_RESET}"
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo ""
echo "    This will remove EVERYTHING related to a ULPF install:"
echo ""
echo "      - Docker containers, volumes, and demo images"
echo "      - Any running background connector processes"
echo "      - ~/.ulpf and ~/.ulpf-connector runtime states"
echo "      - .env and .env.bak.* secrets"
echo "      - backend/venv Python environment"
echo "      - backend/*.db local SQLite databases"
echo "      - frontend/node_modules dependencies"
echo "      - Python caches across the repository"
echo ""
echo "    Source code, git history, and .env.example are NOT touched."
echo ""
echo "  ------------------------------------------------------------"
echo -n "       Type YES to continue, anything else to cancel: "
read -r CONFIRM
echo "  ------------------------------------------------------------"
echo ""

if [[ "$CONFIRM" != "YES" && "$CONFIRM" != "yes" ]]; then
    echo "       Cancelled."
    exit 0
fi

echo "  Starting cleanup..."
echo ""

# ------------------------------------------------------------
# 1. Docker Cleanup
# ------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
    say "Stopping Docker stack..."
    docker compose down --remove-orphans >/dev/null 2>&1 || true

    say "Removing ULPF Docker volumes..."
    docker volume rm -f sih-test_ulpf_pg sih-test_ulpf_minio ulpf_pg ulpf_minio >/dev/null 2>&1 || true

    say "Removing ULPF Docker images..."
    docker rmi -f ulpf-backend:demo ulpf-worker:demo ulpf-frontend:demo >/dev/null 2>&1 || true

    say "Pruning Docker build cache..."
    docker builder prune -f >/dev/null 2>&1 || true
fi

# ------------------------------------------------------------
# 2. Stop running processes
# ------------------------------------------------------------
say "Stopping running connector and dev processes..."
pkill -f "connector.py" >/dev/null 2>&1 || true
pkill -f "uvicorn app.main:app" >/dev/null 2>&1 || true
pkill -f "vite" >/dev/null 2>&1 || true

# ------------------------------------------------------------
# 3. Connector state directories & artifacts
# ------------------------------------------------------------
say "Removing runtime state directories..."
rm -rf "$HOME/.ulpf" 2>/dev/null || true
rm -rf "$HOME/.ulpf-connector" 2>/dev/null || true
rm -rf /tmp/ulpf* 2>/dev/null || true

if [[ -d "$REPO_ROOT/scripts/ulpf-connector" ]]; then
    rm -f "$REPO_ROOT/scripts/ulpf-connector"/*.log 2>/dev/null || true
    rm -f "$REPO_ROOT/scripts/ulpf-connector"/*.jsonl 2>/dev/null || true
    rm -f "$REPO_ROOT/scripts/ulpf-connector"/*.bookmark* 2>/dev/null || true
    rm -f "$REPO_ROOT/scripts/ulpf-connector"/spool* 2>/dev/null || true
fi

# ------------------------------------------------------------
# 4. .env and backups
# ------------------------------------------------------------
say "Removing .env and backups..."
rm -f "$REPO_ROOT/.env" "$REPO_ROOT/.env.bak"* 2>/dev/null || true

# ------------------------------------------------------------
# 5. Local database files
# ------------------------------------------------------------
say "Removing SQLite local databases..."
rm -f "$REPO_ROOT/backend"/*.db "$REPO_ROOT/backend"/*.sqlite* 2>/dev/null || true
rm -rf "$REPO_ROOT/backend/data" 2>/dev/null || true

# ------------------------------------------------------------
# 6. Python venv & npm node_modules
# ------------------------------------------------------------
say "Removing backend virtual environment..."
rm -rf "$REPO_ROOT/backend/venv" 2>/dev/null || true

say "Removing frontend node_modules & dist..."
rm -rf "$REPO_ROOT/frontend/node_modules" "$REPO_ROOT/frontend/dist" 2>/dev/null || true

# ------------------------------------------------------------
# 7. Python caches
# ------------------------------------------------------------
say "Cleaning Python cache files..."
find "$REPO_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$REPO_ROOT" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find "$REPO_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo -e "${CLR_GREEN}  ============================================================${CLR_RESET}"
echo -e "${CLR_GREEN}  ULPF cleanup complete! Everything reset to clean checkout.  ${CLR_RESET}"
echo -e "${CLR_GREEN}  ============================================================${CLR_RESET}"
echo ""
