#!/usr/bin/env bash
# ============================================================
#  ULPF - Host Log Connector (Linux)
#
#  Streams systemd journald and file tail logs to ULPF server.
# ============================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_URL="${ULPF_SERVER_URL:-http://localhost:8000}"

echo "============================================================"
echo "          U L P F   -   L I N U X   C O N N E C T O R"
echo "============================================================"
echo "Target server: ${SERVER_URL}"
echo

# 1. Detect Python 3
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo "ERROR: Python 3 is required. Please install python3 (e.g. apt install python3 python3-pip)."
    exit 1
fi

echo "[*] Using Python: $($PY_CMD --version)"

# 2. Bootstrap connector files if missing (standalone download mode)
if [ ! -f "$DIR/connector.py" ]; then
    echo "[*] Downloading connector package from ${SERVER_URL}..."
    TMP_ZIP="/tmp/ulpf-connector-linux.zip"
    curl -fsSL "${SERVER_URL}/api/v1/connectors/download/bundle?os=linux" -o "$TMP_ZIP" || {
        echo "ERROR: Failed to download connector bundle from ${SERVER_URL}"
        exit 1
    }
    unzip -q -o "$TMP_ZIP" -d "$DIR"
    rm -f "$TMP_ZIP"
    echo "[*] Connector package extracted."
fi

# 3. Check / install dependencies
if ! $PY_CMD -c "import httpx" >/dev/null 2>&1; then
    echo "[*] Installing httpx dependency..."
    $PY_CMD -m pip install --quiet --user httpx 2>/dev/null || $PY_CMD -m pip install --quiet httpx
fi

# 4. Prepare configuration
CONFIG_DIR="$HOME/.ulpf"
mkdir -p "$CONFIG_DIR"
CONFIG_PATH="$CONFIG_DIR/connector.json"

if [ ! -f "$CONFIG_PATH" ]; then
    echo "[*] Initializing connector config..."
    if [ -f "$DIR/config.example.json" ]; then
        cp "$DIR/config.example.json" "$CONFIG_PATH"
    fi
fi

# Ensure server URL is configured
if [ -f "$CONFIG_PATH" ]; then
    $PY_CMD -c "
import json
path = '$CONFIG_PATH'
try:
    with open(path, 'r') as f:
        data = json.load(f)
    if '$SERVER_URL' != 'http://localhost:8000' or not data.get('ulpf_base'):
        data['ulpf_base'] = '$SERVER_URL'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
except Exception:
    pass
" 2>/dev/null || true
fi

echo
echo "============================================================"
echo "  ULPF Linux Connector: Real-Time Telemetry Streaming"
echo "  Connecting to: ${SERVER_URL}"
echo "  Configuration: ${CONFIG_PATH}"
echo "  Adapters: Linux journald, file tail"
echo "  Press Ctrl+C to stop."
echo "============================================================"
echo

exec $PY_CMD "$DIR/connector.py" --config "$CONFIG_PATH" --debug-events "$@"
