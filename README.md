# Northstar — AI Goal-Based Financial Planning

> Plan, simulate, and reach every financial goal with an AI copilot built for serious investors.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Overview

Northstar is a full-stack financial planning platform that combines:

- **Monte Carlo simulation** — 10 000 paths per goal to produce real confidence intervals
- **AI Copilot** — GPT-4o-powered advisor anchored to your actual financial data
- **Goal-based planning** — retirement, home, education, travel, emergency and wealth goals tracked independently
- **Optimization engine** — automatically suggests the minimum changes needed to bring an at-risk goal back on track

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (React 19 + TanStack Router)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Dashboard   │  │  Goals CRUD  │  │   AI Copilot     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ REST  /api/v1
┌────────────────────────────▼────────────────────────────────┐
│  FastAPI 0.115  (Python 3.12)                               │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Auth   │  │  Goals   │  │ Simulate │  │  Copilot   │  │
│  └─────────┘  └──────────┘  └──────────┘  └────────────┘  │
│       ↓              ↓             ↓               ↓        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Services: MonteCarlo · Optimizer · PlanningService  │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │ asyncpg
┌────────────────────────────▼────────────────────────────────┐
│  PostgreSQL 16                                               │
│  users · goals · simulations                                 │
└─────────────────────────────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for the full design.

---

## Quick Start

**Native development is the primary, first-class workflow** — no Docker
Desktop required. Pick the setup for your OS below. Containers (Apple's
`container` CLI on macOS, or Docker/OCI) remain fully supported for testing
the production image and for CI/CD — see
[Production Deployment](#production-deployment) — but they are not required
for day-to-day development.

### Prerequisites

| Tool | macOS | Linux | Windows |
|------|-------|-------|---------|
| PostgreSQL 16 | Homebrew | apt/dnf | winget |
| Python 3.12+ | Homebrew/pyenv | apt/dnf | python.org / winget |
| Bun (preferred) or Node 22+/npm | [bun.sh](https://bun.sh) | [bun.sh](https://bun.sh) | [bun.sh](https://bun.sh) |
| `make` (optional but recommended) | Xcode CLT | build-essential | via WSL2 or run scripts directly |

Redis is *not* required — nothing in the app uses it yet. Setup scripts
install it on macOS/Linux anyway since it's provisioned for a future
Redis-backed rate limiter (see `AUDIT.md` #12); skip it if you'd rather not.

Clone and configure once, regardless of OS:

```bash
git clone https://github.com/your-org/northstar.git
cd northstar
```

### Native macOS Setup (recommended)

```bash
./scripts/setup_mac.sh   # installs Homebrew Postgres/Redis, creates the
                          # Python venv, runs migrations, installs frontend deps
make dev                  # or: ./scripts/dev.sh
```

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:8080     |
| Backend  | http://localhost:8000     |
| API docs | http://localhost:8000/docs (when `DEBUG=true`) |

Frontend port note: `bun run dev` actually serves on **8080** (set by the
shared `@lovable.dev/vite-tanstack-config` preset's sandbox port detection,
not this repo's own `vite.config.ts`) — not Vite's conventional 5173.
`CORS_ORIGINS` in `.env.example` includes both.

`setup_mac.sh` is idempotent — safe to re-run. It won't overwrite an
existing `backend/.env`.

### Apple Container (macOS 26+, Apple Silicon)

If you're on a compatible Mac and want to build/run the production image
the same way CI does, but without Docker Desktop, use Apple's open-source
[`container`](https://github.com/apple/container) CLI. It runs OCI images
in lightweight per-container Linux VMs — the Dockerfile in `backend/`
needs no changes.

```bash
# One-time: install the signed .pkg from
# https://github.com/apple/container/releases, then:
container system start

# Build and run the backend image (assumes Postgres is reachable — see below)
make container-build
make container-run
# ...or directly:
container build -t northstar-backend:local ./backend
container run --rm -it -p 8000:8000 --env-file backend/.env northstar-backend:local
```

Notes:
- Requires macOS 26+ and Apple silicon; there's no Intel Mac support. Use
  Docker or native setup instead on unsupported machines.
- There's no `container compose` equivalent yet, so this path is best for
  exercising the backend image in isolation (e.g. before a release), not for
  full multi-service orchestration — use native setup or
  `make docker-up` for that.
- To let the containerized backend reach a Homebrew Postgres running on the
  host, point `DATABASE_URL` in `backend/.env` at your Mac's LAN IP (not
  `localhost`, which resolves inside the container's own VM), or set up
  `container system dns` per [Apple's how-to guide](https://github.com/apple/container/blob/main/docs/how-to.md).

### Native Linux Setup

```bash
./scripts/setup_linux.sh   # apt (Debian/Ubuntu) or dnf (Fedora/RHEL)
make dev                    # or: ./scripts/dev.sh
```

Same URLs and idempotency notes as macOS above. For other package managers,
install PostgreSQL/Redis/`python3-venv` yourself first, then re-run the
script — it detects already-running services and skips installation.

### Native Windows Setup

```powershell
.\scripts\setup_windows.ps1
```

Installs PostgreSQL via `winget`, creates the Python venv, and installs
frontend dependencies. **Redis has no supported native Windows build** —
this script does not install it (see [Troubleshooting](#troubleshooting) if
you need it locally). After setup, run the backend and frontend dev servers
from Git Bash, WSL2, or two separate PowerShell windows:

```powershell
# Terminal 1
cd backend; .venv\Scripts\Activate.ps1; uvicorn app.main:app --reload

# Terminal 2
cd code; bun run dev
```

`make`/`scripts/dev.sh` need a POSIX shell — use WSL2, or Git Bash
(`bash scripts/dev.sh`), if you want the combined dev command on Windows.

### Common Commands

Once set up (any OS), the `Makefile` wraps the day-to-day workflow:

| Command | Does |
|---------|------|
| `make dev` | Run backend + frontend together |
| `make migrate` | `alembic upgrade head` (or `ARGS="downgrade -1"`, etc.) |
| `make test` | Backend pytest + frontend type check/build — same as CI |
| `make lint` | ruff + mypy + eslint — same as CI |
| `make seed` | Seed a demo user + sample goals (idempotent) |
| `make reset-db` | Drop + recreate the local DB, then migrate |
| `make help` | List every available command |

---

## Production Deployment

A few things that are easy to get wrong deploying this app. See `AUDIT.md`
for the full history and rationale. **Docker/OCI images remain the
supported production and CI/CD path** — `backend/Dockerfile` and
`docker-compose.yml` are unchanged and still exercised by
`.github/workflows/ci.yml`'s "Docker build check" job. Nothing about the
native/Apple-Container developer workflow above affects this.

```bash
docker build -t northstar-backend:prod ./backend
docker compose up --build   # full local stack, Docker/OCI-style
```

### Schema comes from Alembic only

`alembic upgrade head` must be run against every environment before the app
serves traffic — the backend does **not** auto-create tables on startup.
There is no fallback; a fresh database with no migrations applied will 404/500
on first request.

### Cross-origin cookies require exact configuration

The refresh token is delivered as an `httpOnly` cookie, which only works
cross-origin (frontend and backend on different domains, the normal case here)
if all of the following hold:
- `CORS_ORIGINS` lists the frontend's **exact** origin(s) — no wildcard, since
  wildcard origins can't be combined with `allow_credentials=True`.
- The frontend must send `credentials: "include"` on every request (already
  done in `code/src/lib/api.ts`).
- Both frontend and backend must be served over HTTPS in production —
  `DEBUG=false` makes the cookies `Secure` + `SameSite=None`, which browsers
  refuse to send over plain HTTP.

### Behind a load balancer or reverse proxy

Set `TRUSTED_PROXY_IPS` to the LB's IP(s), or the rate limiter will key every
request off the LB's own IP instead of the real client, effectively sharing
one rate-limit bucket across all traffic. Leave it empty (default) for a
single-instance deployment with no proxy in front.

### Rate limiting is in-memory, per-process

Fine for one instance. The moment this runs as more than one process/replica,
each gets its own counters and the effective limit multiplies by instance
count. Move to a Redis-backed limiter before scaling horizontally.

### Known gaps not covered by this pass

- **No email/SMS delivery** for password resets — `/auth/forgot-password`
  only returns the reset token when `DEBUG=true`; there is currently no way
  for a real user to receive it in production. Needs an email provider
  integration before this flow is usable end-to-end.
- **No per-user cap on Copilot (OpenAI) usage** — only the generic rate
  limiter throttles this endpoint, so cost exposure is bounded by request
  rate, not by user or by spend.
- **No refresh-token revocation list** — a leaked refresh token remains valid
  until it expires or is rotated by use; there's no way to force-invalidate
  one early (e.g., on "sign out everywhere" or a detected compromise).
- **Copilot has no real conversation memory** — each message is answered
  independently; `conversation_id` is echoed back but prior turns aren't
  replayed to the model.

## Project Structure

```
northstar/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py           # Application factory
│   │   ├── config.py         # Pydantic settings
│   │   ├── database.py       # Async SQLAlchemy engine
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── routers/          # FastAPI route handlers
│   │   ├── services/         # Business logic
│   │   └── middleware/       # Auth dependency injection
│   ├── tests/                # pytest test suite
│   ├── alembic/              # Database migrations (sole source of schema truth)
│   ├── scripts/
│   │   └── seed_data.py      # Demo user + sample goals (see scripts/seed.sh)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile            # OCI image — CI + production, unchanged by native dev support
│   └── .env.example
├── code/                     # TanStack Start frontend
│   ├── src/
│   │   ├── routes/           # TanStack Router pages
│   │   ├── components/       # React components + shadcn/ui
│   │   ├── lib/
│   │   │   ├── api.ts        # API client (real + mock fallback)
│   │   │   └── mock-data.ts  # Development fixtures
│   │   └── styles.css        # Tailwind CSS v4 design tokens
│   └── package.json
├── scripts/                  # Native dev tooling — setup, dev loop, migrations, tests, etc.
│   ├── setup_mac.sh
│   ├── setup_linux.sh
│   ├── setup_windows.ps1
│   ├── dev.sh
│   ├── migrate.sh
│   ├── test.sh
│   ├── lint.sh
│   ├── seed.sh
│   └── reset_db.sh
├── docs/
│   ├── architecture.md
│   ├── backend.md
│   ├── frontend.md
│   └── database.md
├── docker-compose.yml         # OCI/Docker path — CI + production, not required for dev
├── Makefile                   # `make help` for the full command list
├── README.md                  # ← you are here
├── CONTRIBUTING.md
├── CHANGELOG.md
└── CLAUDE.md
```

---

## Running Tests

```bash
make test                       # backend pytest + frontend type check — same as CI
make test ARGS="-k login"       # forward args to pytest, e.g. run a subset

# equivalent, run directly:
cd backend && source .venv/bin/activate
pytest                          # unit + integration (80% coverage required)
pytest tests/test_monte_carlo.py -v   # simulation engine only
pytest --cov=app --cov-report=html    # HTML coverage report
```

---

## API Reference

Full OpenAPI spec available at `/docs` when `DEBUG=true`. The table below is
a quick reference, not exhaustive — see `/docs` or `docs/backend.md` for the
complete route list (profile, financials, assumptions, and reports routers
aren't listed here).

| Method | Path                      | Description                     |
|--------|---------------------------|---------------------------------|
| POST   | /api/v1/auth/register     | Create account                  |
| POST   | /api/v1/auth/login        | Get JWT tokens                  |
| POST   | /api/v1/auth/refresh      | Rotate tokens                   |
| GET    | /api/v1/auth/me           | Current user profile            |
| GET    | /api/v1/goals             | List goals                      |
| POST   | /api/v1/goals             | Create goal                     |
| GET    | /api/v1/goals/{id}        | Get single goal                 |
| PATCH  | /api/v1/goals/{id}        | Update goal                     |
| DELETE | /api/v1/goals/{id}        | Soft-delete goal                |
| GET    | /api/v1/dashboard         | Aggregated metrics              |
| POST   | /api/v1/simulate          | Run Monte Carlo simulation      |
| POST   | /api/v1/simulate/optimize | Get optimisation suggestions    |
| POST   | /api/v1/copilot           | AI chat message                 |
| GET    | /health                   | Health check                    |

---

## Troubleshooting

**`psql: error: connection to server ... failed` after `setup_mac.sh`/`setup_linux.sh`**
The Postgres service may not have started yet. Check with
`brew services list` (macOS) or `systemctl status postgresql` (Linux), and
re-run the setup script — it's idempotent.

**`ModuleNotFoundError` / import errors running backend commands directly**
You forgot to activate the venv: `source backend/.venv/bin/activate`. Every
`scripts/*.sh` does this itself, so prefer `make dev`/`make test`/etc. over
running `uvicorn`/`pytest` by hand.

**Frontend can't reach the backend (`net::ERR_CONNECTION_REFUSED`)**
Check `code/.env.local` has `VITE_API_BASE_URL=http://localhost:8000/api/v1`
and that the backend is actually running (`make dev` starts both). Leaving
`VITE_API_BASE_URL` unset intentionally switches the frontend to mock data —
useful for frontend-only work, but it means nothing is really talking to
your local backend.

**Login/refresh works over `curl` but not from the browser (cookies missing)**
The refresh-token cookie requires `CORS_ORIGINS` in `backend/.env` to
exactly match the frontend origin you're browsing from (`http://localhost:8080`
by default) — no wildcards, since credentialed CORS forbids them. If you
changed the frontend port, update `CORS_ORIGINS` too.

**`alembic upgrade head` fails with "relation already exists"**
Something created tables outside of Alembic (e.g. an old checkout, or manual
`CREATE TABLE`). Easiest fix for a local dev DB: `make reset-db` (drops and
recreates it, then migrates cleanly). Never do this against a database with
data you care about.

**Need Redis locally on Windows**
There's no supported native Windows build. Easiest options: run the app from
inside WSL2 and follow `scripts/setup_linux.sh` there, or install
[Memurai](https://www.memurai.com/) (a Redis-compatible Windows service).
Neither is required today — nothing in the app uses Redis yet.

**Apple Container: `container: command not found`**
Install the signed `.pkg` from the
[releases page](https://github.com/apple/container/releases) — it's not
distributed via Homebrew. Requires macOS 26+ and Apple silicon; there is no
Intel Mac support. Use Docker or native setup instead if your machine doesn't
qualify.

**Apple Container: backend can't reach a Homebrew Postgres on the host**
`localhost` inside a `container run` resolves to the container's own
lightweight VM, not your Mac. Point `DATABASE_URL` at your Mac's LAN IP, or
configure `container system dns` — see the
[Apple Container setup](#apple-container-macos-26-apple-silicon) section
above.

**CI's "Docker build check" fails locally when I try to reproduce it**
That job runs on GitHub's Linux runners with plain Docker — if you're on a
Mac without Docker Desktop, use `make container-build` (Apple Container) or
install Docker just for this one check; it isn't part of the native dev loop.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT © 2025 Northstar Planning
