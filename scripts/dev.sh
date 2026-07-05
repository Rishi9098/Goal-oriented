#!/usr/bin/env bash
#
# Runs backend (uvicorn --reload) and frontend (Vite dev server) together.
# Assumes native setup already ran (scripts/setup_mac.sh / setup_linux.sh).
# Ctrl+C stops both.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
CODE_DIR="$ROOT_DIR/code"

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "backend/.venv not found. Run scripts/setup_mac.sh or scripts/setup_linux.sh first." >&2
  exit 1
fi

pids=()
cleanup() {
  echo
  echo "Stopping..."
  for pid in "${pids[@]}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

echo "==> Backend  http://localhost:8000  (docs at /docs when DEBUG=true)"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &
pids+=("$!")

echo "==> Frontend http://localhost:5173"
if command -v bun >/dev/null 2>&1; then
  ( cd "$CODE_DIR" && exec bun run dev ) &
else
  ( cd "$CODE_DIR" && exec npm run dev ) &
fi
pids+=("$!")

wait
