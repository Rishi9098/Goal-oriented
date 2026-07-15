# Goal-Based Financial Planning Platform — Architecture v2

Supersedes ARCHITECTURE.md for implementation purposes. ARCHITECTURE.md
is kept for historical reference. This document is the single source of
truth for Phase 1 build.

---

## Changelog from v1

| Item | v1 | v2 | Source |
|---|---|---|---|
| Return distribution | `rng.multivariate_normal` (normal) | Correlated Student-t, df=4 | COMPETITOR_ANALYSIS.md §4.1 |
| `confidence_pct` semantics | Optimizer weight (`confidence_weight` in `goal_results`) | Branch comparison: two result rows per probabilistic goal | COMPETITOR_ANALYSIS.md §4.6 |
| `goal_results` schema | Has `confidence_weight numeric(5,4)` | Removes `confidence_weight`; adds `scenario_branch` enum | COMPETITOR_ANALYSIS.md §4.6 |
| `users` schema | No tax regime field | Adds `tax_regime enum(old_regime, new_regime, not_specified)` | MARKET_CONTEXT.md §2.8 |
| Employer contributions | Not modeled; noted as gap | New `employer_contributions` table | MARKET_CONTEXT.md §2.2, §2.5 |
| Disclaimer text | SEBI-only | Covers both SEBI and IRDAI | MARKET_CONTEXT.md §3 intro |
| Disclaimer enforcement | "Prominent on every output page" (intention) | Hard layout wrapper at `(app)/layout.tsx` router level | COMPETITOR_ANALYSIS.md §4.9 |
| `debt_mean_pct` default | 7.0% | 6.5% | MARKET_CONTEXT.md §4.2 (125 bps repo cuts in 2025) |
| `simulation_configs` | No distribution shape param | Adds `return_dist_df integer` default 4 | COMPETITOR_ANALYSIS.md §4.1 |
| Auth | "Supabase Auth or NextAuth.js, defer if personal" | NextAuth v4, JWT strategy, Credentials provider, user profiles in own `users` table | Build prompt locked decisions |
| Phase 1 tables | All tables from v1 | Excludes `allocation_plans`, `goal_allocations`, `tradeoff_suggestions` (optimizer phase) | Build prompt |
| Caste-category scheme matching | Not addressed | Flagged as DPDP-sensitive; not implemented | Build prompt item 6 |
| LP objective formula | `w_j = priority_weight[j] × confidence_pct[j] / 100` (ARCHITECTURE.md §4.4) | `w_j = priority_weights[goal_id]` (priority alone; `confidence_pct` explicitly absent) | Phase 2 clarification pass |

---

## Table of Contents

1. [Locked Decisions](#1-locked-decisions)
2. [Regulatory Line](#2-regulatory-line)
3. [Data Model — v2](#3-data-model--v2)
4. [Calculation and Simulation Architecture — v2](#4-calculation-and-simulation-architecture--v2)
5. [Authentication Architecture](#5-authentication-architecture)
6. [MVP Scope](#6-mvp-scope)
7. [Deferred Items](#7-deferred-items)

---

## 1. Locked Decisions

These are closed. Do not re-open without a separate architecture review.

- **Public, multi-tenant product.** Auth and per-user data isolation are
  required from day 1.
- **Greenfield repo.** If the working directory is not empty before
  scaffolding, stop and report.
- **Two-service architecture.** Next.js 14 (App Router, TypeScript)
  frontend + FastAPI (Python 3.12) backend. Not a single-service
  alternative.
- **Deployment target.** Vercel (frontend) + Railway or Render (backend
  + Postgres). FastAPI BackgroundTasks for simulation jobs, not Celery.
- **Per-goal corpus segregation.** Every goal has its own result and
  allocation rows. No unified pool.
- **Simple income mode.** Default UI: current salary + growth rate +
  one career-break toggle. Full multi-segment schema exists underneath;
  UI exposes it incrementally.

---

## 2. Regulatory Line

Unchanged from ARCHITECTURE.md §2, with one addition.

### 2.1 Disclaimer text (updated — covers both SEBI and IRDAI)

Every output surface at or below `(app)/layout.tsx` must display:

> "This is a mathematical projection, not investment or insurance advice.
> Some instruments shown may be regulated by SEBI (mutual funds, bonds)
> or IRDAI (insurance and ULIP products). Consult a SEBI-registered
> Investment Adviser for investment-related decisions, and a licensed
> insurance adviser for insurance-related products."

### 2.2 Structural enforcement

The disclaimer must be implemented as a hardcoded layout wrapper at
the `app/(app)/layout.tsx` route group level — not as a prop, not as
a component that pages optionally import. The disclaimer text must be
hardcoded inside the component; it is not a configurable prop. A CI
lint rule should fail if any new route under `(app)/` renders without
the wrapper in scope.

### 2.3 Government scheme matching — DPDP flag

MARKET_CONTEXT.md §2.9 covers two government schemes (CSIS and Dr.
Ambedkar Central Sector Scheme) that require caste-category data (OBC/
EBC) to assess eligibility. Collecting caste-category is sensitive
personal data under India's Digital Personal Data Protection Act 2023,
beyond ordinary PII. Do not implement any feature that collects this
field or matches a user profile against these schemes. The government
and private scheme catalogs from MARKET_CONTEXT.md §2–3 ship as static
informational content only — no personalized eligibility matching —
until this is reviewed with a compliance adviser.

---

## 3. Data Model — v2

PostgreSQL 16. SQLAlchemy 2.0 (async). All UUIDs generated server-side.

### Phase 1 tables (implemented now)

`users`, `income_segments`, `employer_contributions`, `goals`,
`simulation_configs`, `simulation_runs`, `goal_results`.

### Phase 2 tables (optimizer — not yet)

`allocation_plans`, `goal_allocations`, `tradeoff_suggestions` are
defined in ARCHITECTURE.md §3.7–3.9 and will be implemented in the
optimizer phase. They are noted in commented stubs in the migration.

---

### 3.1 users

```sql
user_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid()
email             TEXT        NOT NULL UNIQUE
hashed_password   TEXT        NOT NULL
name              TEXT
age               INTEGER     CHECK (age >= 0 AND age <= 120)
monthly_take_home NUMERIC(12,2)
risk_profile      TEXT        CHECK (risk_profile IN ('conservative','moderate','aggressive'))
tax_regime        TEXT        NOT NULL DEFAULT 'not_specified'
                              CHECK (tax_regime IN ('old_regime','new_regime','not_specified'))
created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
```

**v2 change**: Added `tax_regime`. Materially changes after-tax return
of PPF, ELSS, NPS (80CCD(1B)) and ULIP instruments. The old tax regime
permits 80C deductions; the new regime does not. Default `not_specified`
forces the UI to ask rather than assuming.

**Auth note**: `hashed_password` is bcrypt-hashed. NextAuth Credentials
provider verifies against this column. No adapter tables required; JWT
sessions are stateless.

---

### 3.2 income_segments

```sql
segment_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid()
user_id           UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
from_year         INTEGER     NOT NULL
to_year           INTEGER     -- NULL = open-ended (current ongoing segment)
monthly_amount    NUMERIC(12,2) NOT NULL CHECK (monthly_amount >= 0)
annual_growth_pct NUMERIC(5,2) NOT NULL DEFAULT 0
segment_type      TEXT        NOT NULL
                  CHECK (segment_type IN ('salary','break','windfall','freelance'))
```

Simple mode maps to: one row with `segment_type='salary'`, `to_year=NULL`,
plus optionally one `segment_type='break'` row covering the career-break
year range. Full segment editing is accessible but not the primary UI.

---

### 3.3 employer_contributions

**v2 addition.** Employer NPS and EPF contributions bypass the user's
take-home pay entirely — they flow directly into retirement accounts.
They must not be added to `income_segments` (which models take-home
cash available for SIP) because that would inflate the computed monthly
capacity and produce wrong cross-goal allocations.

These are modeled as pre-committed recurring contributions toward the
retirement goal and treated as additions to `existing_corpus` accruing
each year in the simulation.

```sql
contribution_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid()
user_id            UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
contribution_type  TEXT        NOT NULL
                   CHECK (contribution_type IN ('nps_employer','epf_employer'))
monthly_amount     NUMERIC(12,2) NOT NULL CHECK (monthly_amount > 0)
effective_from_year INTEGER    NOT NULL
effective_to_year   INTEGER    -- NULL = ongoing
```

**Computation rule**: For any retirement goal simulation, the sum of
employer_contributions.monthly_amount × 12 for each year in the
simulation horizon is added to that year's corpus accumulation as a
guaranteed contribution — separate from the user's discretionary SIP.
This is analogous to an `additional_monthly_contribution` that is not
drawn from take-home capacity.

**Note on EPF**: Only the 3.67% employer-to-PF portion (not the full
12% employer contribution) counts as retirement corpus. The remaining
8.33% goes to EPS (pension scheme) and EDLI (insurance). Users should
enter the actual PF-credited amount, not the gross employer contribution.
The UI should prompt: "Your employer's PF contribution (not the full
12% — check your payslip)."

---

### 3.4 goals

```sql
goal_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid()
user_id           UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
label             TEXT        NOT NULL
category          TEXT        NOT NULL
                  CHECK (category IN (
                    'education_self','education_child','marriage',
                    'housing','healthcare','retirement','custom'
                  ))
today_cost        NUMERIC(14,2) NOT NULL CHECK (today_cost > 0)
target_year       INTEGER     NOT NULL
confidence_pct    INTEGER     NOT NULL DEFAULT 100
                  CHECK (confidence_pct >= 0 AND confidence_pct <= 100)
inflation_rate    NUMERIC(5,2) NOT NULL   -- e.g. 10.00 for 10%
existing_corpus   NUMERIC(14,2) NOT NULL DEFAULT 0
priority          INTEGER     NOT NULL DEFAULT 0
flexibility       TEXT        NOT NULL DEFAULT 'fixed'
                  CHECK (flexibility IN ('fixed','shiftable','reduceable'))
max_shift_years   INTEGER     -- populated when flexibility = 'shiftable'
max_reduce_pct    NUMERIC(5,2) -- populated when flexibility = 'reduceable'
created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
```

**confidence_pct semantics (v2)**: This field is a display label and
branch-selector, not an optimizer weight. Values below 100 trigger two
simulation result rows per run (see §3.6). The planner does not
interpolate or weight by this value; it shows the user both branches
and lets them decide which plan to fund toward.

---

### 3.5 simulation_configs

```sql
config_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid()
user_id           UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
n_simulations     INTEGER     NOT NULL DEFAULT 1000
equity_mean_pct   NUMERIC(5,2) NOT NULL DEFAULT 12.0
equity_std_pct    NUMERIC(5,2) NOT NULL DEFAULT 18.0
debt_mean_pct     NUMERIC(5,2) NOT NULL DEFAULT 6.5   -- v2: was 7.0; lowered per repo rate cuts
debt_std_pct      NUMERIC(5,2) NOT NULL DEFAULT 3.0
eq_debt_corr      NUMERIC(4,3) NOT NULL DEFAULT -0.150
return_dist_df    INTEGER     NOT NULL DEFAULT 4      -- v2: Student-t degrees of freedom
glide_path_enabled BOOLEAN    NOT NULL DEFAULT true
created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
```

**`return_dist_df` (v2 addition)**: Controls the degrees of freedom for
the Student-t return distribution. df=4 produces fat tails consistent
with observed equity return kurtosis. df=∞ recovers the normal
distribution. The block-bootstrap alternative (resample from actual
NSE Nifty 50 history) is the planned follow-up; the Student-t is the
interim fix per COMPETITOR_ANALYSIS.md §4.1.

**`debt_mean_pct` default lowered from 7.0 to 6.5**: The RBI cut the
repo rate by 125 bps across 2025 (6.5% → 5.25%). Debt fund forward
returns are currently in the 6.5–7.0% range; 7.0% was the top of the
range and is now optimistic. This default is a named assumption, clearly
labeled in the UI, and user-adjustable.

---

### 3.6 simulation_runs

```sql
run_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid()
user_id           UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
config_snapshot   JSONB       NOT NULL  -- frozen config at run time; no FK dependency
status            TEXT        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','running','complete','failed'))
label             TEXT        -- e.g. "Plan A — delay marriage 2 years"
error_message     TEXT        -- populated on status='failed'
created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
completed_at      TIMESTAMPTZ
```

---

### 3.7 goal_results

One or two rows per (run, goal). Two rows when `goals.confidence_pct < 100`.

```sql
result_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid()
run_id            UUID        NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE
goal_id           UUID        NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE
scenario_branch   TEXT        NOT NULL DEFAULT 'goal_included'
                  CHECK (scenario_branch IN ('goal_included','goal_excluded'))
                  -- 'goal_excluded': goal doesn't happen; SIP = 0, prob = 100%
                  -- Always produced when confidence_pct < 100
future_cost_p50   NUMERIC(14,2) NOT NULL
future_cost_p95   NUMERIC(14,2) NOT NULL
success_prob_pct  NUMERIC(5,2)  NOT NULL
required_sip_p50  NUMERIC(12,2) NOT NULL
required_sip_p80  NUMERIC(12,2) NOT NULL
shortfall_p25     NUMERIC(14,2) NOT NULL  -- shortfall at 25th-pct corpus outcome
equity_start_pct  NUMERIC(5,2)  NOT NULL
equity_end_pct    NUMERIC(5,2)  NOT NULL
used_monthly_timestep BOOLEAN  NOT NULL  -- true when horizon <= 7 years

UNIQUE (run_id, goal_id, scenario_branch)
```

**v2 changes**:
- Removed `confidence_weight numeric(5,4)` — confidence_pct is no longer
  an optimizer input.
- Added `scenario_branch` — distinguishes the "goal happens" from "goal
  doesn't happen" computation.
- Added `used_monthly_timestep` — documents which simulation path was
  taken; useful for debugging and for frontend display ("simulation used
  monthly timestep for precision on this near-term goal").
- Added `UNIQUE (run_id, goal_id, scenario_branch)` — enforces that
  exactly one row per branch per (run, goal).

**`goal_excluded` row semantics**: When `scenario_branch = 'goal_excluded'`:
- `future_cost_p50 = 0`, `future_cost_p95 = 0`
- `success_prob_pct = 100.0`
- `required_sip_p50 = 0`, `required_sip_p80 = 0`
- `shortfall_p25 = 0`
- `equity_start_pct` and `equity_end_pct` are still populated (the
  allocation that would have applied, for informational display)

---

### 3.8 Deferred tables (optimizer phase)

The following tables are defined in ARCHITECTURE.md §3.7–3.9 and are
noted in a commented block in the Phase 1 migration. They are not
implemented until the optimizer phase.

```
-- PHASE 2: allocation_plans, goal_allocations, tradeoff_suggestions
-- See ARCHITECTURE.md §3.7-3.9 for full schema.
-- Implement when the cross-goal LP solver is built.
```

---

## 4. Calculation and Simulation Architecture — v2

### 4.1 Where the math runs

Unchanged from ARCHITECTURE.md §4.1. Server-side Python, async via
FastAPI BackgroundTasks. Client-side pre-estimate (100 simulations,
TypeScript Web Worker) for slider responsiveness — purely illustrative,
never persisted.

### 4.2 Monte Carlo engine — v2 (Student-t, not normal)

**Change from v1**: Replace `rng.multivariate_normal` with a correlated
Student-t distribution via Gaussian-chi² decomposition. This is the
interim fix for fat-tail underestimation; block bootstrap off actual
NSE Nifty 50 history is the planned follow-up (see §7).

```python
def _sample_t_returns(
    rng, equity_mean, equity_std, debt_mean, debt_std,
    corr, df, n_sims, n_periods
) -> np.ndarray:  # shape (n_sims, n_periods, 2)
    """
    Correlated Student-t via Gaussian / chi-squared decomposition.

    For T ~ t(df) with desired std sigma_target:
        Var(T) = sigma_scale^2 * df/(df-2)
    So to achieve sigma_target, use:
        sigma_scale = sigma_target * sqrt((df-2)/df)

    The resulting distribution has:
        Mean = equity_mean / debt_mean (for df > 1)
        Std  = equity_std  / debt_std  (for df > 2)
        Kurtosis = 6/(df-4) above normal (for df > 4; at df=4, excess kurtosis = ∞)
    """
    var_factor = df / (df - 2)            # variance inflation vs N(0,1)
    eq_scale = equity_std / np.sqrt(var_factor)
    dt_scale = debt_std  / np.sqrt(var_factor)

    cov = np.array([
        [eq_scale**2,             corr * eq_scale * dt_scale],
        [corr * eq_scale * dt_scale, dt_scale**2            ],
    ])

    # Normal component (shape of the correlation structure)
    z = rng.multivariate_normal([0.0, 0.0], cov, size=(n_sims, n_periods))

    # Chi-squared component (degree of tail fatness)
    chi2 = rng.chisquare(df=df, size=(n_sims, n_periods))
    scale = np.sqrt(chi2 / df)            # shape (n_sims, n_periods)

    # Assemble t-samples and shift by means
    t = z / scale[:, :, np.newaxis]      # fat-tailed zero-mean
    t[:, :, 0] += equity_mean
    t[:, :, 1] += debt_mean
    return t
```

### 4.3 Timestep selection

- Horizon > 7 years: annual simulation (fast; precision adequate).
- Horizon ≤ 7 years: monthly simulation (captures near-term volatility;
  annual draws are too few for calibrated probabilities).

Annual parameters are converted to monthly for the short-horizon path:
```python
monthly_mean = (1 + annual_mean) ** (1/12) - 1
monthly_std  = annual_std / sqrt(12)   # approximate; adequate for planning
```

Glide-path window: 5 annual periods (annual path) or 60 monthly
periods (monthly path), always measured from the end of the horizon.

### 4.4 Confidence_pct — branch comparison (v2)

For any goal with `confidence_pct < 100`, the simulation module runs
the full Monte Carlo **twice** and returns two `GoalSimulationResult`
objects:

1. `scenario_branch='goal_included'`: full simulation; goal is treated
   as certain and the required SIP is computed normally.
2. `scenario_branch='goal_excluded'`: trivial result; SIP=0,
   success_prob=100%, shortfall=0. Represents the plan if the uncertain
   goal does not happen.

The frontend displays both branches side by side. The user decides
which branch to fund toward. The planner never blends or interpolates
by `confidence_pct`; that number is a display label only.

Goals with `confidence_pct = 100` produce exactly one result row
(`goal_included`).

### 4.5 Cross-goal allocation solver — LP objective (replaces ARCHITECTURE.md §4.4)

**LP objective formula as implemented** (replaces the stale
`w_j = priority_weight[j] × confidence_pct[j] / 100` in the original):

```
maximize  Σ_j  w_j · t_j

where  t_j  ≈  p_j(sip_j)   (auxiliary variable for the piecewise-linear
                               approximation of success-probability curve)
       w_j  =  priority_weights[goal_id]     if caller supplies the dict
            =  1.0                            otherwise (uniform weights)

Caller convention:  w_j = float(goal.priority)  (from the goals table)
                    with a minimum of 1.0 for any goal in the run.
```

**confidence_pct is not used by the optimizer.** This was an explicit
Phase 1 decision (COMPETITOR_ANALYSIS.md §4.6): confidence_pct triggers
a branch comparison in the simulation layer (two result rows: goal_included
/ goal_excluded), but it is never passed to or read by `solve_allocation()`.
Zero references to `confidence_pct` exist in `app/engine/optimizer.py` —
verified by grep.

**Branch invariant:** `solve_allocation()` only receives goals from the
user's selected branch. The API layer is responsible for:
1. Running `run_all_goals()` to get both branches for any goal with
   `confidence_pct < 100`.
2. Presenting both branches to the user (or using the user's saved branch
   selection from a previous session).
3. Passing only the goals from the selected branch to `solve_allocation()`.

Excluded-branch goals (`scenario_branch='goal_excluded'`) never enter the
LP. If a user selects the "goal excluded" branch, that goal simply does not
appear in the goals list passed to the optimizer.

**A3 fat-tail quantification — t(df=4) vs matched normal (10,000 sims):**

| Horizon | t(4) P1/P99 spread | Normal P1/P99 spread | Ratio | Delta |
|---|---|---|---|---|
| 4yr monthly (48 periods) | ₹2,06,227 | ₹2,01,656 | 1.0227 | +2.27% |
| 15yr annual (15 periods) | ₹46,92,250 | ₹46,20,757 | 1.0155 | +1.55% |

The short-horizon path shows slightly more fat-tail advantage (+2.27% vs
+1.55%). The difference is modest in absolute terms but consistent in
direction: fewer compounding steps means less CLT dilution of the
single-period tail. Neither horizon produces the theoretical single-period
advantage (~14% at P1/P99) because corpus variance is dominated by the
deterministic SIP accumulation component at these time horizons.

**verification_diverged flag** is in:
- Python `AllocationPlan` dataclass (field `verification_diverged: bool`)
- SQLAlchemy `AllocationPlan` ORM model (`Mapped[bool]`)
- Alembic migration 002 (`BOOLEAN NOT NULL DEFAULT false`)

It is set to `True` when the post-LP Monte Carlo verification detects that
any goal's achieved probability diverges from the LP-predicted probability
by more than 5 percentage points AND the LP is re-run with 15 sample points.
It is NOT a log-only field — it is stored in the `allocation_plans` row so
a plan that required re-verification is visibly marked in the DB and API
response.

### 4.6 Technology stack

```
Frontend        Next.js 14 (App Router) + TypeScript
                App Router route groups: (auth) and (app)
                Disclaimer wrapper: app/(app)/layout.tsx — router level
                Auth: NextAuth v4, JWT, Credentials provider
                Web Worker: 100-sim pre-estimate in TypeScript (later phase)

Backend API     FastAPI 0.115+ (Python 3.12)
                Pydantic v2 for all request/response models
                Async SQLAlchemy 2.0 with asyncpg driver
                BackgroundTasks for simulation job dispatch
                API keys for B2B2C licensing (first-class from day 1)

Simulation      Pure Python module: app/engine/monte_carlo.py
                numpy, scipy — no HTTP dependencies
                Student-t via Gaussian/chi² decomposition
                Independently testable without API stack

Database        PostgreSQL 16
                SQLAlchemy 2.0 (async) ORM
                Alembic for migrations (one migration file per phase)

Auth            NextAuth v4 with Credentials provider
                bcryptjs for password hashing (frontend)
                bcrypt (Python) for verification option on backend
                JWT sessions — no adapter tables required
                Users stored in our own `users` table

Deployment      Vercel (frontend)
                Railway or Render (FastAPI + PostgreSQL)
```

---

## 5. Authentication Architecture

### 5.1 Choice: NextAuth v4, JWT, Credentials

**NextAuth v4** (not v5/Auth.js — v5 is still beta with breaking API
changes that would require rework at the next minor release).

**JWT sessions** (not database sessions): session data is stored in a
signed, encrypted cookie. No adapter tables needed. User identity is
verified by looking up `users.email` in our DB on each credential
check; subsequent requests use the JWT without a DB query.

**Credentials provider**: email + bcrypt-hashed password. User
registers → password hashed with bcryptjs → stored in `users.hashed_password`.
Login → bcrypt.compare → NextAuth issues JWT.

### 5.2 Per-user data isolation

Every table with user-specific data has `user_id UUID NOT NULL REFERENCES
users(user_id) ON DELETE CASCADE`. The FastAPI API extracts `user_id`
from the request's auth header (passed from Next.js server components)
and applies it as a WHERE filter on all queries. No row may be accessed
without matching `user_id`.

**API authentication**: Next.js server components call the FastAPI
backend with an `Authorization: Bearer <jwt>` header. FastAPI verifies
the JWT using the shared `NEXTAUTH_SECRET`. The `get_current_user`
dependency in `app/api/deps.py` does this verification and returns the
`user_id` from the token payload.

### 5.3 API-key layer for B2B2C (future)

The FastAPI app accepts two authentication modes from day 1:
1. JWT (from NextAuth, for the consumer product)
2. API key header (`X-API-Key`) — for future RIA/AMC white-label
   licensing (COMPETITOR_ANALYSIS.md §4.5)

Phase 1 ships with JWT only. The API key path is stubbed in `deps.py`
with a `NotImplementedError` comment, not a silent fallback.

---

## 6. MVP Scope

### 6.1 Phase 1 (this build)

- User registration and login (NextAuth Credentials)
- Goal CRUD with all fields from §3.4
- Income segment entry (simple mode: one salary segment + optional break)
- Employer contributions table (NPS and EPF)
- Simulation run dispatch via BackgroundTasks
- Monte Carlo engine: Student-t, per-goal glide path, branch comparison,
  short-horizon monthly timestep
- `goal_results` storage with both scenario branches where applicable
- Disclaimer wrapper enforced at router level

### 6.2 Not in Phase 1

- Cross-goal allocation solver (allocation_plans, goal_allocations,
  tradeoff_suggestions tables)
- PDF export
- Frontend goal/simulation UI pages (routing skeleton only)
- Government/private scheme catalog pages
- Client-side pre-estimate Web Worker
- Staleness banner and re-run UI
- Annual plan-review email

---

## 7. Deferred Items and Follow-ups

| Item | Description | Source |
|---|---|---|
| Block bootstrap | Replace Student-t with actual NSE Nifty 50 rolling return resampling | COMPETITOR_ANALYSIS.md §4.1 |
| Engagement loop | Annual plan-review email + staleness banner | COMPETITOR_ANALYSIS.md §4.10, §4.8 |
| PDF export | Pre-generate on run completion; store in object storage | COMPETITOR_ANALYSIS.md §4.7 |
| Scheme catalog pages | Static informational content; no user matching | MARKET_CONTEXT.md §2–3 |
| CSIS/Ambedkar eligibility matching | Requires caste-category data; DPDP review first | Build prompt item 6 |
| Short-horizon LP fix | 10–15 sample points + post-LP MC verification | COMPETITOR_ANALYSIS.md §4.2 |
| NPS partial withdrawal | Retirement goal model should account for partial withdrawals permitted for education/housing | MARKET_CONTEXT.md §2.2 |
| Tax regime impact on returns | After-tax return differs significantly between regimes for NPS/PPF/ELSS | MARKET_CONTEXT.md §2.8 |
