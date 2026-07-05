#!/usr/bin/env bash
#
# Runs Alembic migrations. Defaults to "upgrade head"; pass through any other
# alembic subcommand/args, e.g.:
#   scripts/migrate.sh                              # upgrade head
#   scripts/migrate.sh downgrade -1
#   scripts/migrate.sh revision --autogenerate -m "add foo column"

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

if [[ $# -eq 0 ]]; then
  alembic upgrade head
else
  alembic "$@"
fi
