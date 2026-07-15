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
│   │   ├── simulation.py    # Simulation + Optimisation + Chat schemas
│   │   └── family.py        # Milestone 2 Task 2: Family CRUD schemas
│   ├── routers/
│   │   ├── auth.py          # /auth/* (login/refresh use httpOnly cookies)
│   │   ├── goals.py         # /goals/*
│   │   ├── dashboard.py     # /dashboard
│   │   ├── simulate.py      # /simulate  /simulate/optimize
│   │   ├── copilot.py       # /copilot
│   │   ├── profile.py       # /profile
│   │   ├── financials.py    # /financials/*
│   │   ├── assumptions.py   # /assumptions
│   │   ├── reports.py       # /reports/summary
│   │   └── family.py        # /family/* (Milestone 2 Task 2 — onboarding-seed, member CRUD)
│   ├── services/
│   │   ├── monte_carlo.py   # Core simulation engine
│   │   ├── optimizer.py     # Optimisation strategy generator
│   │   ├── planning_service.py # Dashboard aggregation + health score
│   │   ├── auth_service.py  # Token creation/verification
│   │   ├── family_service.py # Milestone 2 Task 2: household/member business logic
│   │   └── scheme_eligibility_service.py # Milestone 2 Task 3: eligibility evaluation
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

A fast 2 000-path variant (`quick_probability`/`quick_probability_async`) is used for two purposes, both seeded from `MONTE_CARLO_SEED` when set:

- **Optimizer probes** (`services/optimizer.py`) — read-only exploration, results never persisted.
- **`calculate_goal_probability`** (`services/planning_service.py`) — the single, centralized place a goal's stored `probability`/`on_track` is computed and persisted. Called only from goal create/update (`routers/goals.py`) — never from a read endpoint. See ADR-001 (`ArchitectureDecisionRecord.md`) and the "Calculation Lifecycle" section in `docs/architecture.md` for the full rule and rationale.

## Optimizer

`services/optimizer.py` — `generate_suggestions()`

Generates up to 5 ranked suggestions by probing three strategy families:

1. **Contribution increase** — $50, $100, $200, $500 increments
2. **Risk profile shift** — one step up the conservative → balanced → aggressive ladder
3. **Combination** — +$100/mo + risk shift

Each probe calls `quick_probability` to estimate the projected confidence. Results are sorted by projected probability descending and capped at 5.

## Scheme Eligibility Evaluation (Milestone 2 Task 3)

`services/scheme_eligibility_service.py` evaluates a household's members against `scheme_eligibility_rules` — deliberately only three `rule_type`s (`max_age`, `min_age`, `gender`), matching exactly what's been seeded and verified in `GovernmentPolicyReport.md`. This is **not** a general rule interpreter — a fourth `rule_type` gets added only when a scheme actually needs one and a verified fact backs it, per `docs/ENGINEERING_CONSTITUTION.md` Rule 7.

Two entry points, both routing through the same per-member rule evaluation (`_evaluate_rules_for_member`) so eligibility logic is never duplicated between consumers:
- `evaluate_household_eligibility()` — the full three-bucket (eligible / potentially_eligible / not_eligible) view, for the Family Government Schemes screen (Task 11, not yet built).
- `check_ssy_eligibility()` — a single-scheme check reused by `family_service.create_member`/`update_member` for the Add-Child inline callout.

A `min_age` rule not yet met is bucketed `potentially_eligible` rather than `not_eligible` if the member is within 5 years of the threshold (a product decision, not a policy fact — see `DesignReview.md`). This doesn't apply to `max_age` ceilings: once a child ages out of SSY, there's no "potentially eligible by getting older" direction.

Age is computed via exact calendar-date arithmetic (`year - year - (month, day) comparison`), not `days / 365.25` — the latter drifts across an exact boundary (e.g. a precise 10th birthday) depending on leap days in the specific span measured, caught while writing this task's boundary tests.

## Family Member Detail (Milestone 2 Task 7)

`family_service.is_complete()` (renamed from a private `_is_complete()`, previously used only internally by `list_members_with_completeness()` for the Family Home list) is now also called directly from `create_family_member`/`update_family_member`/`get_family_member`, so `FamilyMemberResponse.is_complete` is available on every family-member response, not just the list. This exists specifically so the frontend never has to re-derive completeness from raw fields — the same lesson PCA-2 already established for household summaries applies here too. `DELETE /family/members/{id}` (soft-delete only, `is_active=false`) was already built in Task 2; Task 7 is its first real frontend consumer.

## Family Goals & Custom Inflation (Milestone 2 Task 9)

`goals.custom_inflation_rate` (schema-only since migration 007) is now settable via the existing `PATCH /api/v1/goals/{goal_id}` (bound `[0, 0.5]`, matching `FinancialAssumptions.inflation_rate`'s own bound) and returned on `GoalResponse`. **This field is deliberately outside `planning_service.CALCULATION_CONTEXT_FIELDS`** — it feeds a separate, on-the-fly future-cost projection computed entirely on the frontend (`current_cost × (1 + rate)^years`), never the Monte Carlo probability engine. Wiring real inflation-aware Monte Carlo is explicitly Milestone 4 (Calculation Engine) scope, per `Milestone2ImplementationContract.md` §9 — see `CalculationContextReview.md` for the full reasoning, including a tension between this task's own brief and the Contract that was surfaced to and resolved by the user before implementation.

`planning_service.CALCULATION_CONTEXT_FIELDS` is now the single source of truth for "what triggers a probability recompute" — `routers/goals.py`'s `update_goal()` only calls `calculate_goal_probability()` when the PATCH body includes at least one of these five fields. This closes a real gap: the endpoint previously recalculated unconditionally on *any* field change (including `name`, `priority`, and now `custom_inflation_rate`), which — since `settings.monte_carlo_seed` is unset in dev — silently perturbed `probability` via RNG variance on every edit, not just Calculation Context ones.

`routers/family.py`'s `get_family_member` now populates `eligible_schemes` on its response — a pre-existing gap from Task 7 (only `create_family_member`/`update_family_member` ever set it) found while wiring this task's SSY callout, which is the first thing to read that field from a `GET`. Guarded with the same `if dependent else []` pattern already used for every other dependent-derived field on that response, since the "self" member has no `dependent` row and would otherwise crash `scheme_eligibility_service`'s `dependent.date_of_birth` access.

## Family Insurance (Milestone 2 Task 10)

`app/services/family_insurance_service.py` (new) implements the family-floater-vs-standalone-parent-policy recommendation as a **calculation-lite fact application** — deliberately not a Milestone 5 Recommendation Engine output. `compute_insurance_recommendation()` is computed fresh on every `GET /family/insurance` call, never persisted to the pre-existing `recommendations`/`recommendation_citations` tables (which remain completely unused — confirmed via a direct query, zero rows across the database). This is a considered decision: the computation is a pure, deterministic function of current household state with no RNG, so recomputing on read carries none of the risk ADR-001 was written to eliminate, and writing a row on every read would itself reintroduce the "GET mutates stored data" anti-pattern PCA-3 already found and fixed elsewhere. See `RecommendationIntegrityReview_Task10.md` for the full reasoning.

The base ₹25,000 80D deduction figure is read from the seeded `tax_sections` table (`section_number='80D'`) rather than hardcoded. The ₹50,000 senior-citizen figure is derived structurally (`base_limit × 2`, per `FamilyHUFPlanningReport.md`/`GovernmentPolicyReport.md`'s verified 2× relationship), not a second literal that could drift out of sync with the base figure.

`scheme_eligibility_service._age_years()` was promoted to public `age_years()` and is reused here for senior-citizen (60+) determination — pure date arithmetic, not scheme-evaluation logic, so this does not blur the schemes/insurance boundary (`Scheme`/`SchemeEligibilityRule`/`SchemeRate` are never read by this service, and `TaxSection`/`health_policies` are never read by `scheme_eligibility_service`).

A parent is excluded from triggering the recommendation if already covered by an **active** policy on file, even if their `has_own_insurance` answer (captured at onboarding/Task 6) is stale — the actual coverage data is the more current signal. The trigger condition is `has_own_insurance != 'yes'` (covers `'no'`, `'not_sure'`, and an unanswered value) rather than the Contract's more literal two-value enum check, resolved in favor of the Acceptance Criteria's "all parents marked yes" framing — see `DataIntegrityReview_Task10.md`.

## Family Recommendations (Milestone 2 Task 11)

**A task-identity mismatch was found and resolved before implementation.** This turn's brief was titled "Task 11 (Family Recommendations)" but described aggregating multiple recommendation sources with conflict detection — content that matches `Milestone2ImplementationContract.md`'s **Task 12** (Family Dashboard's recommendation feed), not its actual Task 11 (a single-source "Family Government Schemes" screen). Documented and confirmed with the user in `DependencyValidation_Task11.md` before writing any code, rather than guessed at silently.

`app/services/family_recommendations_service.py` (new) aggregates Task 10's `family_insurance_service.compute_insurance_recommendation()` and Task 3's `scheme_eligibility_service.evaluate_household_eligibility()` into one `GET /family/recommendations` response. It performs zero eligibility math and zero deduction-figure computation of its own — every value is read from an already-certified engine, never recomputed. This reuses Task 3's eligibility-evaluation function directly rather than depending on a dedicated Schemes screen existing first.

Every `FamilyRecommendation`, regardless of source, carries `why`/`why_now`/`what_information_was_used`/`what_information_is_missing`/`confidence_score` — mandatory fields on the shared schema, never optionally populated. Scheme recommendations are built only from the `"eligible"` bucket (never `"potentially_eligible"`/`"not_eligible"`), with `confidence_score` fixed at `1.0` since eligibility here is a deterministic rule match, not a probabilistic estimate.

**Conflict detection is genuine, not decorative.** A conflict is defined narrowly: two recommendations sharing a subject *and* a `reference_code` (the same bounded deduction/scheme ceiling) — e.g., an insurance recommendation (reference code `"80D"`) and a scheme recommendation about the *same person* (reference code `"80C/123"`) are **not** flagged, since they draw from different tax sections and are genuinely compatible advice. With the currently seeded schemes (SSY matches only children under 10, SCSS matches only seniors 60+), the mechanism correctly never fires — verified by construction and live, not assumed. See `RecommendationConflictReview_Task11.md`. If a conflict were ever detected, both recommendations remain in the response; conflicts are additive context, never a suppression mechanism (no hardcoded source priority).

`InsuranceRecommendation` (Task 10) gained an additive `subjects: list[str]` field, populated from data the engine already computes internally — exposed so the aggregation layer can group/conflict-check without re-deriving who a recommendation concerns.

## Family Dashboard (Milestone 2 Task 12)

`app/services/family_dashboard_service.py` (new) backs `GET /family/dashboard` — a **read-only composition layer** with a strict property: it contains zero financial arithmetic (only counting, set membership, and min-by-date selection). Every figure is a persisted value (goal `probability`/`on_track`/`target_date`, set only by the Calculation Lifecycle's write paths per ADR-001) or the verbatim output of an existing certified service: `family_service.list_members_with_completeness`/`list_goals_with_tags`, `family_insurance_service.list_policies_with_coverage`/`uncovered_parents`, `family_recommendations_service.get_family_recommendations` (called verbatim — the feed is byte-identical to `GET /family/recommendations`, enforced by test), and `planning_service.get_dashboard` (passthrough of `liquid_assets`/`monthly_expenses`).

**Two Contract deviations, documented in `DependencyValidation_Task12.md`:**
1. The Contract's "existing emergency-fund-months calculation" does not exist in the codebase. Rather than invent backend logic (forbidden by this task's own "no financial calculations on read" constraint), the endpoint passes through `get_dashboard()`'s two authoritative figures and the frontend renders "X months covered" as display arithmetic — Task 9's exact precedent.
2. The Parents card's literal Contract condition (raw `has_own_insurance != 'yes'`) would contradict the recommendations feed whenever a stale answer coexists with an on-file policy. `family_insurance_service.uncovered_parents()` was extracted from `compute_insurance_recommendation()` (pure refactor, all Task 10 tests pass unchanged) so the card and the recommendation share one authority and cannot disagree.

**Partial failures degrade gracefully:** each card computes under its own guard — a failure is logged with full context (`family_dashboard_section_failed`) and that card arrives as `null` (rendered "unavailable", never a fake zero) while every other section populates. A failed recommendations feed sets `recommendations_unavailable: true`, distinguishable from the honest empty state. Nothing is ever persisted by this endpoint — freshness after data changes falls out of statelessness, not cache invalidation.

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

### Household Ownership (Milestone 2 Task 2)

Every other resource in this codebase is scoped by a direct `WHERE ... user_id = current_user.id` filter. `family_service.resolve_owned_household()` is the first exception: a household is resolved via `households.created_by_user_id = current_user.id` **or** a `household_members` row linking the user to that household — written against the general rule (per `Milestone2ImplementationContract.md` §2) even though, for Milestone 2 specifically (no shared household logins yet), it always resolves via `created_by_user_id` in practice. Every `member_id`/household-scoped path parameter is then re-checked against that resolved household — a mismatch returns `404`, never `403`, matching the existing convention of not confirming another resource's existence to an unauthorized caller. `get_or_create_household()` wraps this with a lazy-provision fallback (used by every Family endpoint, not just `GET /family`) so an authenticated user is never blocked by a missing household row.

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
