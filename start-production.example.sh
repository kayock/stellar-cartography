#!/usr/bin/env bash
# Example production-style launcher (safe for public repos).
# Copy to start-production.sh (gitignored) and set your Stellarium URL.
set -euo pipefail
cd "$(dirname "$0")"

# Optional: allow an extra LAN host for local TTS endpoints (Father Fox / Kayock Voice).
# export STELLAR_CARTOGRAPHY_TTS_HOSTS=192.168.1.10

export STELLAR_CARTOGRAPHY_HOST="${STELLAR_CARTOGRAPHY_HOST:-0.0.0.0}"
export STELLAR_CARTOGRAPHY_PORT="${STELLAR_CARTOGRAPHY_PORT:-8775}"
export STELLAR_CARTOGRAPHY_STELLARIUM_URL="${STELLAR_CARTOGRAPHY_STELLARIUM_URL:-http://127.0.0.1:8090}"

exec ./start.sh \
  --host "$STELLAR_CARTOGRAPHY_HOST" \
  --port "$STELLAR_CARTOGRAPHY_PORT" \
  --no-browser \
  --stellarium-url "$STELLAR_CARTOGRAPHY_STELLARIUM_URL" \
  "$@"
