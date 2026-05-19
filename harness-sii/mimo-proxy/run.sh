#!/usr/bin/env bash
# ---------------------------------------------------------------
# mimo-proxy launcher
#
# Usage (CPU node – has internet):
#   cd harness-sii/mimo-proxy
#   bash run.sh
#
# The proxy listens on 0.0.0.0:8080 by default.
# GPU node can access it via SSH port-forward:
#   ssh -L 8080:localhost:8080 cpu-node
#
# Then set in .env:
#   LLM_BASE_URL=http://localhost:8080/v1
# ---------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

# Create venv if missing
if [ ! -d .venv ]; then
    echo "[mimo-proxy] Creating virtualenv …"
    python3 -m venv .venv
fi

# Activate
# shellcheck disable=SC1091
source .venv/bin/activate

# Install / upgrade deps
pip install -q --upgrade pip
pip install -q -r requirements.txt

PORT="${MIMO_PROXY_PORT:-8080}"
HOST="${MIMO_PROXY_HOST:-0.0.0.0}"

echo "[mimo-proxy] Starting on ${HOST}:${PORT} …"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --log-level info
