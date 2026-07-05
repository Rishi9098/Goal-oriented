#!/usr/bin/env bash
#
# Native macOS setup for Northstar — no Docker Desktop required.
#
# Installs/starts Homebrew PostgreSQL (+ Redis, provisioned for future use —
# the app does not depend on it today), creates a Python virtualenv, installs
# frontend dependencies via Bun, and bootstraps backend/.env.
#
# Apple Silicon on macOS 26+: if you want to build/run the production
# container image without Docker Desktop, see "Apple Container" in
# README.md — that's a separate, optional workflow from this script.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
CODE_DIR="$ROOT_DIR/code"

PG_VERSION="${PG_VERSION:-16}"
DB_NAME="${DB_NAME:-northstar}"
DB_USER="${DB_USER:-northstar}"
DB_PASSWORD="${DB_PASSWORD:-northstar}"
# Overridable: if you already have a PostgreSQL instance (Postgres.app, the
# postgresql.org installer, another Homebrew version) bound to 5432, set
# DB_PORT to something free, e.g.: DB_PORT=5433 ./scripts/setup_mac.sh
DB_PORT="${DB_PORT:-5432}"

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$1" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$1" >&2; exit 1; }

port_in_use() {
  # A real connection attempt, not a process-table inspection: `lsof` only
  # shows sockets owned by processes the current user can see, so it misses
  # a system-installed PostgreSQL running as its own dedicated `postgres`
  # OS user (the official postgresql.org installer does this, and it's
  # common enough that this check must not rely on lsof).
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

[[ "$(uname)" == "Darwin" ]] || die "This script is for macOS. Use scripts/setup_linux.sh or scripts/setup_windows.ps1 instead."

command -v brew >/dev/null 2>&1 || die "Homebrew not found. Install it from https://brew.sh and re-run this script."

log "Installing PostgreSQL ${PG_VERSION} and Redis via Homebrew"
brew list "postgresql@${PG_VERSION}" >/dev/null 2>&1 || brew install "postgresql@${PG_VERSION}"
brew list redis >/dev/null 2>&1 || brew install redis

# Homebrew's versioned postgresql@N formulas are keg-only (not on PATH).
BREW_PG_PREFIX="$(brew --prefix "postgresql@${PG_VERSION}")"
export PATH="$BREW_PG_PREFIX/bin:$PATH"
PG_DATA_DIR="$(brew --prefix)/var/postgresql@${PG_VERSION}"

if [[ -f "$PG_DATA_DIR/postgresql.conf" ]]; then
  if grep -qE '^port = [0-9]+' "$PG_DATA_DIR/postgresql.conf"; then
    sed -i '' "s/^port = .*/port = ${DB_PORT}/" "$PG_DATA_DIR/postgresql.conf"
  else
    printf '\nport = %s\n' "$DB_PORT" >> "$PG_DATA_DIR/postgresql.conf"
  fi
fi

# A conflict here means some *other* server already owns this port — our own
# instance can't be listening yet, since we haven't started it below. This
# is the single most common way this script fails on a real dev machine
# (Postgres.app, the postgresql.org installer, etc. all default to 5432 too).
if port_in_use "$DB_PORT"; then
  die "Port ${DB_PORT} is already in use by another PostgreSQL (or other) server
(common cause: Postgres.app, or the postgresql.org installer, which runs as
its own 'postgres' OS user — 'lsof' as yourself won't show it, but it's
still there). Either stop that server, or run this script against a free
port:
  DB_PORT=5433 ./scripts/setup_mac.sh"
fi

log "Starting PostgreSQL and Redis as background services"
brew services start "postgresql@${PG_VERSION}"
brew services start redis

log "Waiting for PostgreSQL to accept connections on port ${DB_PORT}"
# -h localhost forces a TCP connection instead of the default Unix socket.
# This matters: an unrelated PostgreSQL install (Postgres.app, the
# postgresql.org installer, etc.) can leave its own socket at the same
# default path (/tmp/.s.PGSQL.<port>), and an unqualified `psql`/`pg_isready`
# would silently connect to *that* server instead of the one this script
# just started — TCP has no such ambiguity.
PSQL_HOST_ARGS=(-h localhost -p "$DB_PORT")
ready=false
for _ in $(seq 1 30); do
  if pg_isready -q "${PSQL_HOST_ARGS[@]}" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  die "PostgreSQL did not report ready on port ${DB_PORT} after 30s. Check the log:
  brew services info postgresql@${PG_VERSION}
  tail -50 $(brew --prefix)/var/log/postgresql@${PG_VERSION}.log"
fi

log "Creating database role and database (idempotent)"
psql postgres "${PSQL_HOST_ARGS[@]}" -tc "SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}'" | grep -q 1 \
  || psql postgres "${PSQL_HOST_ARGS[@]}" -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}' CREATEDB;"
psql postgres "${PSQL_HOST_ARGS[@]}" -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 \
  || psql postgres "${PSQL_HOST_ARGS[@]}" -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

log "Setting up backend/.env"
if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(64))')"
  # BSD sed (macOS) requires an explicit (empty) backup-suffix argument to -i.
  sed -i '' "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${JWT_SECRET}|" "$BACKEND_DIR/.env"
  sed -i '' "s|^DEBUG=.*|DEBUG=true|" "$BACKEND_DIR/.env"
  sed -i '' "s|^ENVIRONMENT=.*|ENVIRONMENT=development|" "$BACKEND_DIR/.env"
  sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}|" "$BACKEND_DIR/.env"
  log "Generated backend/.env with a fresh JWT secret (DEBUG=true for local dev)"
else
  log "backend/.env already exists — leaving it untouched (if DB_PORT differs from what's in it, migrations below will fail — update DATABASE_URL manually)"
fi

log "Creating Python virtual environment"
PYTHON_BIN="python3.12"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || PYTHON_BIN="python3"
[[ -d "$BACKEND_DIR/.venv" ]] || "$PYTHON_BIN" -m venv "$BACKEND_DIR/.venv"

# shellcheck disable=SC1091
source "$BACKEND_DIR/.venv/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r "$BACKEND_DIR/requirements-dev.txt"

log "Running database migrations"
( cd "$BACKEND_DIR" && alembic upgrade head )
deactivate

log "Installing frontend dependencies"
if command -v bun >/dev/null 2>&1; then
  ( cd "$CODE_DIR" && bun install )
elif command -v npm >/dev/null 2>&1; then
  warn "Bun not found — falling back to npm (https://bun.sh is the primary supported tool)"
  ( cd "$CODE_DIR" && npm install )
else
  die "Neither Bun nor npm found. Install Bun from https://bun.sh (or Node.js/npm) and re-run."
fi

if [[ ! -f "$CODE_DIR/.env.local" ]]; then
  echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > "$CODE_DIR/.env.local"
  log "Created code/.env.local pointing at the local backend"
fi

log "Setup complete."
cat <<'EOF'

Next steps:
  ./scripts/dev.sh          start backend + frontend together
  ./scripts/test.sh         run backend + frontend test/verify suites
  make help                 list all available commands

Apple Silicon on macOS 26+: to build/run the production container image
without Docker Desktop, see "Apple Container" in README.md.
EOF
