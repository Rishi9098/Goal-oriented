#!/usr/bin/env bash
#
# Runs the same lint/type-check gates as CI: ruff + mypy (backend), eslint
# (frontend).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
CODE_DIR="$ROOT_DIR/code"

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "backend/.venv not found. Run scripts/setup_mac.sh or scripts/setup_linux.sh first." >&2
  exit 1
fi

echo "==> Backend lint (ruff)"
# shellcheck disable=SC1091
( cd "$BACKEND_DIR" && source .venv/bin/activate && ruff check . )

echo
echo "==> Backend type check (mypy)"
# shellcheck disable=SC1091
( cd "$BACKEND_DIR" && source .venv/bin/activate && mypy app/ )

echo
echo "==> Frontend lint (eslint)"
if command -v bun >/dev/null 2>&1; then
  ( cd "$CODE_DIR" && bun run lint )
else
  ( cd "$CODE_DIR" && npm run lint )
fi

echo
echo "Lint clean."
