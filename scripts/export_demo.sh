#!/usr/bin/env bash
# ============================================================
#  ULPF SIH Demo - Export Script (Linux & macOS)
#  Builds all Docker images and packages into dist/ulpf-demo/
# ============================================================

set -e

CLR_RESET="\033[0m"
CLR_CYAN="\033[1;36m"
CLR_GREEN="\033[1;32m"
CLR_YELLOW="\033[1;33m"
CLR_RED="\033[1;31m"
CLR_BOLD="\033[1m"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPTS_DIR/.." && pwd)"
OUT="$REPO/dist"

echo ""
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo -e "${CLR_CYAN}     ULPF SIH Demo: Export Script (Linux & macOS)            ${CLR_RESET}"
echo -e "${CLR_CYAN}     Builds all Docker images and saves to dist/             ${CLR_RESET}"
echo -e "${CLR_CYAN}  ============================================================${CLR_RESET}"
echo ""

mkdir -p "$OUT"
cd "$REPO"

# 1. Build images
echo "  [1/3] Building Docker images (may take several minutes)..."
if ! docker compose build --no-cache; then
    echo -e "${CLR_RED}  [ERROR] Docker build failed. Verify Docker daemon is running.${CLR_RESET}"
    exit 1
fi
echo -e "        ${CLR_GREEN}[OK]${CLR_RESET} All Docker images built successfully."

# 2. Save images to archive
echo ""
echo "  [2/3] Saving images to archive (~2.5 GB, 3-5 minutes)..."
docker save \
    ulpf-backend:demo \
    ulpf-worker:demo \
    ulpf-frontend:demo \
    postgres:16-alpine \
    redis:7-alpine \
    ghcr.io/wrkode/openbucket:latest \
    -o "$OUT/ulpf-sih-demo-images.tar"

echo -e "        ${CLR_GREEN}[OK]${CLR_RESET} Archive saved: dist/ulpf-sih-demo-images.tar"

# 3. Copy project files
echo ""
echo "  [3/3] Copying project files to dist/ulpf-demo/..."
TARGET_DIR="$OUT/ulpf-demo"
rm -rf "$TARGET_DIR" 2>/dev/null || true
mkdir -p "$TARGET_DIR"

if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude="node_modules" \
             --exclude=".git" \
             --exclude="venv" \
             --exclude=".venv" \
             --exclude="dist" \
             --exclude="__pycache__" \
             --exclude=".pytest_cache" \
             --exclude="*.pyc" \
             --exclude="*.tar" \
             --exclude="*.log" \
             --exclude="*.db" \
             --exclude="*.sqlite*" \
             "$REPO/" "$TARGET_DIR/"
else
    # Fallback to tar
    (cd "$REPO" && tar -cf - \
        --exclude="node_modules" \
        --exclude=".git" \
        --exclude="venv" \
        --exclude=".venv" \
        --exclude="dist" \
        --exclude="__pycache__" \
        --exclude=".pytest_cache" \
        --exclude="*.tar" \
        . | (cd "$TARGET_DIR" && tar -xf -))
fi

echo "        Copying image archive into ulpf-demo/ folder..."
cp "$OUT/ulpf-sih-demo-images.tar" "$TARGET_DIR/ulpf-sih-demo-images.tar"

# Ensure runner permissions
chmod +x "$TARGET_DIR"/*.sh "$TARGET_DIR/scripts"/*.sh 2>/dev/null || true

echo ""
echo -e "${CLR_GREEN}  ============================================================${CLR_RESET}"
echo -e "${CLR_GREEN}    EXPORT COMPLETE!                                          ${CLR_RESET}"
echo ""
echo "    Hand judges the entire dist/ulpf-demo/ folder:"
echo ""
echo "      dist/ulpf-demo/ulpf-sih-demo-images.tar   (~2.5 GB)"
echo "      dist/ulpf-demo/scripts/import_and_run.sh  (Linux/Mac entry)"
echo "      dist/ulpf-demo/scripts/import_and_run.bat (Windows entry)"
echo "      dist/ulpf-demo/README_DEMO.md             (guide)"
echo ""
echo "    On Linux / Mac, the judge runs:"
echo "      ./scripts/import_and_run.sh"
echo -e "${CLR_GREEN}  ============================================================${CLR_RESET}"
echo ""
