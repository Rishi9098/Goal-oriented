# Architecture

## System Overview

Northstar is a two-tier web application: a React SPA frontend and a Python FastAPI backend communicating over a versioned REST API (`/api/v1`). PostgreSQL is the single source of truth for all persistent state.

```
┌─────────────────────────────────────────────────────────────┐
│  Client (Browser)                                           │
│                                                             │
│  TanStack Router  →  Route components  →  api.ts client    │
│                                                             │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS REST
┌──────────────────────────────▼──────────────────────────────┐
│  FastAPI (uvicorn, 4 workers)                               │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Routers  (auth · goals · dashboard · simulate · copilot)│
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Services                                             │  │
│  │   MonteCarlo   — NumPy log-normal path simulation     │  │
│  │   Optimizer    — contribution / risk-shift strategies │  │
│  │   PlanningService — goal refresh, health scoring      │  │
│  │   AuthService  — bcrypt + jose JWT                    │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  SQLAlchemy (async) + asyncpg                         │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               │ TCP
┌──────────────────────────────▼──────────────────────────────┐
│  PostgreSQL 16                                              │
│  tables: users · goals · simulations                        │
└─────────────────────────────────────────────────────────────┘
```

## Design Decisions

### Async-first backend

All database access uses `asyncpg` through SQLAlchemy's async session. This allows a single uvicorn process to handle hundreds of concurrent API requests without blocking threads on I/O — critical when the Monte Carlo simulation (CPU-bound) runs inline with DB reads.

### Monte Carlo inline vs worker queue

The 10 000-path simulation runs in ~80 ms on a modern CPU using NumPy vectorised operations. For a V1 product this is acceptable inline. If the p99 latency exceeds 200 ms in production, move simulation to a Celery/Redis worker and stream results via Server-Sent Events.

### Soft deletes

Goals use `is_active = false` instead of hard DELETE. This preserves the simulation history that references a goal and allows undo.

### JWT authentication

Short-lived access tokens (30 min) + long-lived refresh tokens (7 days). The frontend stores tokens in `localStorage`. For a higher-security deployment, move access tokens to memory and refresh tokens to httpOnly cookies.

### Frontend mock fallback

`api.ts` checks `VITE_API_BASE_URL` at build time. When the variable is absent the client returns fixture data with a 350 ms artificial delay — so the frontend remains fully usable without a running backend.

## Module Boundaries

```
app/
├── models/    — SQLAlchemy ORM models (schema truth)
├── schemas/   — Pydantic in/out models (API contract)
├── routers/   — HTTP handlers, no business logic
├── services/  — Business logic, no HTTP concerns
└── middleware/ — FastAPI dependencies (auth, rate limit)
```

No business logic lives in routers; routers only validate input, delegate to a service, and return a schema.

## Future Architecture

| Concern             | Current                | Next step                          |
|---------------------|------------------------|------------------------------------|
| Simulation latency  | Inline NumPy           | Celery worker + SSE streaming      |
| Account linking     | Manual input           | Plaid / MX read-only OAuth         |
| AI memory           | Stateless per request  | LangChain ConversationBufferMemory |
| Multi-tenancy       | Single PostgreSQL DB   | Row-level security (RLS)           |
| Observability       | uvicorn logs           | OpenTelemetry → Grafana            |
