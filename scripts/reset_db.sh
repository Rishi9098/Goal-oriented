#!/usr/bin/env bash
#
# Drops and recreates the local dev database, then re-runs migrations.
# Always targets the local default DB (DB_NAME/DB_USER/DB_PORT below) via the
# local Postgres instance's trust-auth "postgres" maintenance connection — it
# never reads DATABASE_URL, so it can't accidentally be pointed at a remote
# or production database by an unexpected .env value.
#
# Usage: scripts/reset_db.sh [-y|--yes]
# If your DATABASE_URL uses a non-default port (see setup_mac.sh's DB_PORT
# handling for when that's needed), pass DB_PORT here too so this script
# targets the same server: DB_PORT=5433 scripts/reset_db.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

DB_NAME="${DB_NAME:-northstar}"
DB_USER="${DB_USER:-northstar}"
DB_PORT="${DB_PORT:-5432}"
# -h localhost forces TCP instead of the default Unix socket, which can
# silently belong to a *different* PostgreSQL install listening on the same
# default socket path — see setup_mac.sh for the full explanation.
PSQL_HOST_ARGS=(-h localhost -p "$DB_PORT")

FORCE=false
for arg in "$@"; do
  if [[ "$arg" == "-y" || "$arg" == "--yes" ]]; then
    FORCE=true
  fi
done

echo "This will DROP and recreate the local '${DB_NAME}' database. All data in it will be lost."
if [[ "$FORCE" != true ]]; then
  read -r -p "Continue? [y/N] " reply
  case "$reply" in
    [Yy]*) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

echo "==> Dropping database ${DB_NAME} (if it exists)"
psql postgres "${PSQL_HOST_ARGS[@]}" -c "DROP DATABASE IF EXISTS ${DB_NAME};"

echo "==> Creating database ${DB_NAME}"
psql postgres "${PSQL_HOST_ARGS[@]}" -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

echo "==> Running migrations"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  alembic upgrade head
)

echo "Done. Run scripts/seed.sh if you want demo data."
