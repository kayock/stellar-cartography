#!/usr/bin/env bash
# Stellar Cartography — portable launcher
#
# Starts the local web UI via run.py. Pass through any run.py flags
# (--host, --port, --stellarium-url, --no-browser, --verbose).
#
# Examples:
#   ./start.sh --host 127.0.0.1 --port 8775 --stellarium-url http://127.0.0.1:8090
#   ./start.sh --host 0.0.0.0 --port 8775 --no-browser --stellarium-url http://127.0.0.1:8090
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
    if [ -x .venv/bin/python3 ]; then
        PYTHON=".venv/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON="python3"
    else
        echo "[ERROR] Python 3 not found. Install python3 (>=3.9) and re-run." >&2
        exit 1
    fi
fi

echo "================================================================"
echo " Stellar Cartography"
echo " Using interpreter: $PYTHON"
echo " Starting local web UI... (keep this window open)"
echo "================================================================"
echo

exec "$PYTHON" run.py "$@"
