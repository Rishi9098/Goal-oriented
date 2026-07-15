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
│  │  Routers  (auth · goals · dashboard · simulate · copilot ·│
│  │            profile · financials · assumptions · reports) │
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
│  tables: users · goals · simulations · user_profiles ·      │
│          income_sources · expenses · assets · liabilities · │
│          financial_assumptions · password_reset_tokens      │
└─────────────────────────────────────────────────────────────┘
```

## Design Decisions

### Async-first backend

All database access uses `asyncpg` through SQLAlchemy's async session. This allows a single uvicorn process to handle hundreds of concurrent API requests without blocking threads on I/O — critical when the Monte Carlo simulation (CPU-bound) runs inline with DB reads.

### Monte Carlo inline vs worker queue

The 10 000-path simulation runs in ~80 ms on a modern CPU using NumPy vectorised operations. For a V1 product this is acceptable inline. If the p99 latency exceeds 200 ms in production, move simulation to a Celery/Redis worker and stream results via Server-Sent Events.

### Calculation Lifecycle: read operations never perform or persist financial calculations

**Rule (ADR-001):** a goal's Monte Carlo probability is computed and persisted **only** when its Calculation Context changes — `current_amount`, `monthly_contribution`, `target_date`, `risk_profile`, or `target_amount` — i.e. only on goal create and goal update (`POST`/`PATCH /goals`, via the single centralized `planning_service.calculate_goal_probability()`). Every read (`GET /dashboard`, `GET /reports/summary`, `GET /goals`, the AI Copilot) consumes that same persisted value and never recomputes it.

This closed a Critical product-consistency finding (PCA-3): `GET /dashboard` previously recomputed and overwrote every active goal's probability on every view, using an unseeded RNG — so the same goal could show a different number depending on which screen was opened last, and a boundary-case goal's `on_track` flag could flip between page loads with no user action and no audit trail. See `MonteCarloConsistencyReport.md` and `ArchitectureDecisionRecord.md` (ADR-001) for the full investigation, alternatives considered, and rationale.

Explicitly out of scope for this rule (by design, not oversight): a scheduled/versioned recalculation model (e.g. nightly refresh, full simulation history per goal) was considered and rejected for now — it would require background-job infrastructure this codebase does not have. The existing `simulations` table (append-only, timestamped, input-snapshotted — written only by the explicit `POST /simulate` action) is the right shape for that future work and should be extended rather than duplicated when it's actually needed.

### Soft deletes

Goals use `is_active = false` instead of hard DELETE. This preserves the simulation history that references a goal and allows undo.

### JWT authentication

Short-lived access tokens (30 min) + long-lived refresh tokens (7 days). The access token is kept in `localStorage` (low blast radius given its short lifetime). The refresh token is set as an `httpOnly`, `SameSite` cookie scoped to `/api/v1/auth`, paired with a double-submit CSRF cookie/header — it is never readable by JS, closing the XSS-exfiltration path a fully-localStorage design would have.

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

**Milestone 1 (2026-07-06)** added foundation tables with no routers yet: `models/household.py`, `policy.py` (versioned government scheme/tax data — never hardcoded, see `docs/database.md`), `estate.py`, `insurance.py`, `recommendation.py`, `audit.py`.

**Foundation Reconciliation (2026-07-06)** added `models/company_policy.py` (Policy Engine Layers 2-3: `BestPracticeRule`, `CompanyPolicy`) and a nullable `huf_entity_id` ownership column on the four `financials.py` models — see `FoundationReconciliationReport.md` for the decision log. `user_profiles.dependents`/`marital_status` and `financial_assumptions.tax_rate` are now marked deprecated in code (not removed) in favor of the household/policy entities. See `PROJECT_STATE.md` for full milestone tracking.

## Future Architecture

| Concern             | Current                | Next step                          |
|---------------------|------------------------|------------------------------------|
| Simulation latency  | Inline NumPy           | Celery worker + SSE streaming      |
| Account linking     | Manual input           | Plaid / MX read-only OAuth         |
| AI memory           | Stateless per request  | LangChain ConversationBufferMemory |
| Multi-tenancy       | Single PostgreSQL DB   | Row-level security (RLS)           |
| Observability       | Structured JSON logs + request-ID correlation | OpenTelemetry → Grafana |
