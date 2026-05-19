#!/usr/bin/env bash
# ---------------------------------------------------------------
# mimo-proxy launcher
#
# Usage (CPU node – has internet):
#   cd harness-sii/mimo-proxy
#   bash run.sh
#
# The proxy listens on 127.0.0.1:8088 by default.
# GPU node can access it via SSH port-forward:
#   ssh -L 8088:localhost:8088 cpu-node
#
# Then set in .env:
#   LLM_BASE_URL=http://localhost:8088/v1
# ---------------------------------------------------------------
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "[setup] creating .venv ..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

HOST="${MIMO_PROXY_HOST:-127.0.0.1}"
PORT="${MIMO_PROXY_PORT:-8088}"

echo "[run] uvicorn app.main:app --host $HOST --port $PORT"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --no-access-log
