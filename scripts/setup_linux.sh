#!/usr/bin/env bash
#
# Native Linux setup for Northstar — no containers required.
#
# Installs/starts PostgreSQL (+ Redis, provisioned for future use — the app
# does not depend on it today) via the system package manager, creates a
# Python virtualenv, installs frontend dependencies via Bun, and bootstraps
# backend/.env.
#
# Supports apt (Debian/Ubuntu) and dnf (Fedora/RHEL). For other distros,
# install postgresql/redis/python3-venv yourself, then re-run this script —
# it will detect the running services and skip package installation.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
CODE_DIR="$ROOT_DIR/code"

DB_NAME="${DB_NAME:-northstar}"
DB_USER="${DB_USER:-northstar}"
DB_PASSWORD="${DB_PASSWORD:-northstar}"

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$1" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$1" >&2; exit 1; }

[[ "$(uname)" == "Linux" ]] || die "This script is for Linux. Use scripts/setup_mac.sh or scripts/setup_windows.ps1 instead."

PKG_MANAGER=""
if command -v apt-get >/dev/null 2>&1; then
  PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="dnf"
else
  warn "No supported package manager (apt/dnf) detected. Install PostgreSQL, Redis, and python3-venv manually, then re-run this script."
fi

sudo_if_needed() {
  if [[ "$EUID" -eq 0 ]]; then "$@"; else sudo "$@"; fi
}

case "$PKG_MANAGER" in
  apt)
    log "Installing PostgreSQL, Redis, and Python build deps (apt)"
    sudo_if_needed apt-get update -y
    sudo_if_needed apt-get install -y postgresql postgresql-contrib redis-server python3-venv python3-pip
    ;;
  dnf)
    log "Installing PostgreSQL, Redis, and Python build deps (dnf)"
    sudo_if_needed dnf install -y postgresql-server postgresql-contrib redis python3-pip
    # RHEL/Fedora's postgresql-server needs an explicit first-time initdb.
    if [[ ! -d /var/lib/pgsql/data ]] || [[ -z "$(ls -A /var/lib/pgsql/data 2>/dev/null)" ]]; then
      sudo_if_needed postgresql-setup --initdb
    fi
    ;;
esac

log "Starting PostgreSQL and Redis"
if command -v systemctl >/dev/null 2>&1; then
  sudo_if_needed systemctl enable --now postgresql
  sudo_if_needed systemctl enable --now redis-server 2>/dev/null || sudo_if_needed systemctl enable --now redis
else
  warn "systemctl not available (no systemd?) — start PostgreSQL and Redis yourself, e.g. via 'service postgresql start'."
fi

log "Waiting for PostgreSQL to accept connections"
ready=false
for _ in $(seq 1 30); do
  if sudo_if_needed -u postgres pg_isready -q >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
[[ "$ready" == true ]] || die "PostgreSQL did not report ready after 30s. Check: systemctl status postgresql"

log "Creating database role and database (idempotent)"
sudo_if_needed -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}'" | grep -q 1 \
  || sudo_if_needed -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}' CREATEDB;"
sudo_if_needed -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 \
  || sudo_if_needed -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

log "Setting up backend/.env"
if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(64))')"
  sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${JWT_SECRET}|" "$BACKEND_DIR/.env"
  sed -i "s|^DEBUG=.*|DEBUG=true|" "$BACKEND_DIR/.env"
  sed -i "s|^ENVIRONMENT=.*|ENVIRONMENT=development|" "$BACKEND_DIR/.env"
  sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}|" "$BACKEND_DIR/.env"
  log "Generated backend/.env with a fresh JWT secret (DEBUG=true for local dev)"
else
  log "backend/.env already exists — leaving it untouched"
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
  warn "Bun not found — falling back to npm (curl -fsSL https://bun.sh/install | bash is the primary supported tool)"
  ( cd "$CODE_DIR" && npm install )
else
  die "Neither Bun nor npm found. Install Bun (curl -fsSL https://bun.sh/install | bash) or Node.js/npm and re-run."
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
EOF
