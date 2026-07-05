#!/usr/bin/env bash
#
# Seeds one demo user with sample goals + financial data for local
# development. Safe to re-run — it's a no-op if the demo user already
# exists. See backend/scripts/seed_data.py for the actual data.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "backend/.venv not found. Run scripts/setup_mac.sh or scripts/setup_linux.sh first." >&2
  exit 1
fi

cd "$BACKEND_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate
# Run as a module (not a plain script path) so `app` resolves on sys.path —
# a plain `python scripts/seed_data.py` would only put scripts/ on the path.
python -m scripts.seed_data
