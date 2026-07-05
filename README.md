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

### Prerequisites

- Docker & Docker Compose
- Node.js 22+ / Bun (frontend)
- Python 3.12+ (backend only)

### 1 — Clone and configure

```bash
git clone https://github.com/your-org/northstar.git
cd northstar
cp backend/.env.example backend/.env
# Edit backend/.env — set JWT_SECRET_KEY at minimum
```

### 2 — Start everything with Docker Compose

```bash
docker compose up --build
```

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:5173       |
| Backend  | http://localhost:8000       |
| API docs | http://localhost:8000/docs  |

### 3 — Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4 — Local backend development (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # fill in values
uvicorn app.main:app --reload
```

### 5 — Local frontend development (without Docker)

```bash
cd code
bun install
# Point at local backend or leave VITE_API_BASE_URL blank for mock data
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env.local
bun run dev
```

---

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
│   ├── alembic/              # Database migrations
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
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
├── docs/
│   ├── architecture.md
│   ├── backend.md
│   ├── frontend.md
│   └── database.md
├── docker-compose.yml
├── README.md                 # ← you are here
├── CONTRIBUTING.md
├── CHANGELOG.md
└── CLAUDE.md
```

---

## Running Tests

```bash
cd backend
pytest                          # unit + integration (80% coverage required)
pytest tests/test_monte_carlo.py -v   # simulation engine only
pytest --cov=app --cov-report=html    # HTML coverage report
```

---

## API Reference

Full OpenAPI spec available at `/docs` when `DEBUG=true`.

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT © 2025 Northstar Planning
