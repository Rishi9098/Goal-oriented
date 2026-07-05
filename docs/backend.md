# Backend Reference

## Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Language     | Python 3.12                         |
| Framework    | FastAPI 0.115                       |
| Server       | uvicorn (4 workers in production)   |
| ORM          | SQLAlchemy 2.0 (async)              |
| DB driver    | asyncpg                             |
| Migrations   | Alembic                             |
| Auth         | python-jose (JWT) + passlib (bcrypt)|
| Simulation   | NumPy 2.x                           |
| AI           | openai Python SDK (GPT-4o)          |
| Validation   | Pydantic v2                         |
| Config       | pydantic-settings                   |

## Project Layout

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory + lifespan
│   ├── config.py            # Settings loaded from .env
│   ├── database.py          # Async engine, session factory, Base
│   ├── models/
│   │   ├── user.py          # User ORM model
│   │   ├── goal.py          # Goal ORM model
│   │   ├── financials.py    # Asset / Liability / IncomeSource / Expense
│   │   ├── profile.py       # User profile ORM model
│   │   ├── assumptions.py   # Financial assumptions ORM model
│   │   ├── reset_token.py   # Password reset token ORM model
│   │   └── simulation.py    # Simulation result ORM model
│   ├── schemas/
│   │   ├── user.py          # Register / Login / Token schemas
│   │   ├── goal.py          # Goal CRUD schemas
│   │   ├── financials.py    # Financials CRUD schemas
│   │   ├── profile.py       # Profile schemas
│   │   ├── assumptions.py   # Assumptions schemas
│   │   ├── reports.py       # Report summary schemas
│   │   └── simulation.py    # Simulation + Optimisation + Chat schemas
│   ├── routers/
│   │   ├── auth.py          # /auth/* (login/refresh use httpOnly cookies)
│   │   ├── goals.py         # /goals/*
│   │   ├── dashboard.py     # /dashboard
│   │   ├── simulate.py      # /simulate  /simulate/optimize
│   │   ├── copilot.py       # /copilot
│   │   ├── profile.py       # /profile
│   │   ├── financials.py    # /financials/*
│   │   ├── assumptions.py   # /assumptions
│   │   └── reports.py       # /reports/summary
│   ├── services/
│   │   ├── monte_carlo.py   # Core simulation engine
│   │   ├── optimizer.py     # Optimisation strategy generator
│   │   ├── planning_service.py # Dashboard aggregation + health score
│   │   └── auth_service.py  # Token creation/verification
│   └── middleware/
│       ├── auth.py          # get_current_user FastAPI dependency
│       ├── rate_limit.py    # In-memory token-bucket rate limiter
│       └── request_id.py    # Request ID propagation for log correlation
├── tests/                   # pytest suite
├── alembic/                 # DB migrations — sole source of schema truth
├── requirements.txt
├── requirements-dev.txt
└── Dockerfile
```

## Monte Carlo Engine

`services/monte_carlo.py` — `run_simulation()`

**Method:** log-normal return model.

For each risk profile, annual parameters are:

| Profile      | μ (return) | σ (volatility) |
|--------------|-----------|----------------|
| Conservative | 5.5%      | 7%             |
| Balanced     | 7.5%      | 12%            |
| Aggressive   | 9.5%      | 18%            |

Monthly parameters are derived as:
- `monthly_mu = annual_mu / 12`
- `monthly_sigma = annual_sigma / sqrt(12)`

Each simulation path samples monthly log-returns from `N(μ - σ²/2, σ)`, converts to multiplicative returns, then compounds:

```
portfolio[t+1] = portfolio[t] * return[t] + monthly_contribution
```

The 10 000 terminal values are used to compute:
- **Success rate** — fraction of paths ≥ target amount
- **Percentiles** — p10, p25, p50, p75, p90
- **Distribution** — 50-bin histogram (used by the frontend chart)

A fast 2 000-path variant (`quick_probability`) is used for inline goal refresh and optimizer probes.

## Optimizer

`services/optimizer.py` — `generate_suggestions()`

Generates up to 5 ranked suggestions by probing three strategy families:

1. **Contribution increase** — $50, $100, $200, $500 increments
2. **Risk profile shift** — one step up the conservative → balanced → aggressive ladder
3. **Combination** — +$100/mo + risk shift

Each probe calls `quick_probability` to estimate the projected confidence. Results are sorted by projected probability descending and capped at 5.

## Authentication Flow

```
POST /auth/register  →  hash password (bcrypt)                →  insert User
POST /auth/login     →  verify password                       →  access token in body;
                                                                   refresh token + CSRF
                                                                   token as cookies
POST /auth/refresh   →  read refresh cookie, check CSRF header →  new access token in body;
                                                                   rotated refresh + CSRF cookies
POST /auth/logout    →  clear both cookies
GET  /auth/me        →  decode access JWT                      →  return User
```

Access token lifetime: 30 minutes. Refresh token lifetime: 7 days.

**The refresh token is never returned in a response body** — it's set by the
backend as an `httpOnly` cookie (`ns_refresh_token`, scoped to
`/api/v1/auth`), so client-side JS (and anything that can read `localStorage`,
e.g. XSS) can't read it. A second, readable cookie (`ns_csrf_token`) pairs
with it: the frontend reads that cookie and echoes it back as an
`X-CSRF-Token` header on `/auth/refresh`, and the backend rejects the request
if the header doesn't match the cookie (double-submit CSRF defense — a
cross-site page can't read the CSRF cookie to forge the header). Both cookies
rotate on every successful refresh.

Cookie attributes (`secure`, `samesite`) relax automatically when
`DEBUG=true` so local HTTP dev still works; in production (`DEBUG=false`)
they're `Secure` + `SameSite=None`, which requires HTTPS on both frontend and
backend and an exact (non-wildcard) `CORS_ORIGINS` entry.

All protected endpoints use `get_current_user` (FastAPI `Depends`):
1. Extracts `Authorization: Bearer <token>` header
2. Decodes JWT, validates `type == "access"`
3. Loads `User` from DB, verifies `is_active == true`

## Middleware

Applied in `main.py`, outermost first:

1. **`RateLimitMiddleware`** — in-memory token-bucket, per-IP (or per
   `IP:path` on sensitive routes: login, register, simulate). Only honors
   `X-Forwarded-For` when the direct peer is in `TRUSTED_PROXY_IPS`, and
   evicts stale buckets (LRU cap + TTL sweep) so it can't grow unbounded.
   Single-process only — see the Redis note in the root `README.md`.
2. **`RequestIDMiddleware`** — assigns/propagates a request ID for log
   correlation.
3. **`CORSMiddleware`** — `allow_credentials=True` with an explicit origin
   allowlist (required for the cookie-based refresh flow above).

## Environment Variables

See `.env.example` for the full list. Required variables:

| Variable        | Description                                  |
|-----------------|----------------------------------------------|
| `DATABASE_URL`  | PostgreSQL asyncpg connection string         |
| `JWT_SECRET_KEY`| 64-byte hex secret — generate once, keep safe|

Notable optional variables (all have sane defaults — see `.env.example`):

| Variable                        | Purpose                                                                 |
|----------------------------------|--------------------------------------------------------------------------|
| `TRUSTED_PROXY_IPS`              | Reverse proxy/LB IPs allowed to set `X-Forwarded-For` for the rate limiter. Leave empty with no proxy in front. |
| `RATE_LIMIT_MAX_BUCKETS` / `RATE_LIMIT_BUCKET_TTL_SECONDS` | Caps on the in-memory rate limiter's memory use.       |
| `COOKIE_DOMAIN`                   | Explicit cookie `Domain` attribute for the refresh-token cookie. Leave blank for host-only (the common case). |
| `OPENAI_TIMEOUT_SECONDS` / `OPENAI_MAX_RETRIES` | Bound how long a single Copilot request can hang and how many times the SDK retries transient failures. |
| `MONTE_CARLO_SEED`                | Fixed RNG seed for reproducible simulations. Leave blank for random.    |

## Running Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
pytest --cov=app --cov-report=html   # HTML report in htmlcov/
```

Tests use an in-memory SQLite database via `aiosqlite`. No PostgreSQL required to run the test suite.

## Adding a New Endpoint

1. Define a Pydantic schema in `schemas/`
2. Implement the business logic in `services/`
3. Add a router in `routers/` (thin — only HTTP concerns)
4. Register the router in `main.py`
5. Write integration tests in `tests/`
