#!/usr/bin/env bash
#
# Runs the same checks as CI: backend pytest suite, frontend type check.
# Extra args are forwarded to pytest, e.g.:
#   scripts/test.sh tests/test_auth.py -k login

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
CODE_DIR="$ROOT_DIR/code"

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "backend/.venv not found. Run scripts/setup_mac.sh or scripts/setup_linux.sh first." >&2
  exit 1
fi

echo "==> Backend tests"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pytest "$@"
)

echo
echo "==> Frontend type check + build"
if command -v bun >/dev/null 2>&1; then
  ( cd "$CODE_DIR" && bun run build --mode development )
else
  ( cd "$CODE_DIR" && npm run build -- --mode development )
fi

echo
echo "All checks passed."
