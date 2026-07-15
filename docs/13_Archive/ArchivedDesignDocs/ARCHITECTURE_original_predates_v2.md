# Goal-Based Life Financial Planning Platform — Architecture

Planning pass completed 2026-06-20. Do not start writing code until the
open questions in section 5 are answered — questions 1 and 3 change the
stack and deployment target materially.

---

## Table of Contents

1. [Competitive Landscape](#1-competitive-landscape)
2. [Regulatory Line](#2-regulatory-line)
3. [Data Model](#3-data-model)
4. [Calculation and Simulation Architecture](#4-calculation-and-simulation-architecture)
5. [MVP vs V2 Scope](#5-mvp-vs-v2-scope)
6. [Open Questions](#6-open-questions)

---

## 1. Competitive Landscape

Research conducted 2026-06-20. Covers all players named in the brief plus
Groww, ET Money, INDmoney, Walnut, and Scripbox verified directly.

### 1.1 Product-by-product findings

**Groww**
- Standard SIP/lumpsum/step-up SIP calculators. Goals are labels on SIPs,
  not a planning engine. Deterministic return slider only. No multi-goal
  modeling, no Monte Carlo, no cross-goal conflict math.
- Gap: purely a calculator; not a planning product at all.

**ET Money**
- Goal tracking (label + SIP setup), portfolio health check across 100+
  parameters, fund recommendations powered by "algorithmic analysis."
  Relaunched November 2025 with a stated focus on clarity and simplicity.
- Appears to recommend specific funds — operating as MFD or IA registrant.
  No confirmed Monte Carlo. Goals function as tracking surfaces, not
  forward simulation.
- Gap: the recommendation layer crosses into SEBI IA territory. Planning
  engine underneath is not exposed.

**INDmoney**
- Goal tracker with personalized plan per goal, real-time alignment check
  against actual holdings. Strong multi-asset aggregation (bank, EPF,
  Demat). Automated goal tracking drove a reported 40% retention increase
  in 2024.
- No evidence of Monte Carlo or cross-goal constraint math. Goals are
  tracking and alignment surfaces, not simulation.
- Gap: proves market demand for goal tracking; not a planning engine.

**Walnut / Axio**
- Now fully merged into Axio. SMS-based expense tracker and spend
  categorizer. No SIP planning, no future-value simulation.
- Not a competitor for this problem — it is a budgeting/expense product.

**Scripbox**
- Late-2024 redesign moved to a unified-portfolio model: one SIP across
  all goals, one pool, fewer fund accounts. Recommends specific mutual
  funds directly. Backtested allocation across equity, debt, and gold.
- Named fund recommendations require MFD/IA registration — they hold it.
  The unified-portfolio architecture is actually the right concept but
  implemented as one undifferentiated pool rather than a goal-level
  allocation solver.
- Gap: tied to specific fund recommendations (sales surface); no
  constrained optimization or trade-off surfacing.

**Recipe / Finology**
- Multi-goal priority tracker, SIP allocation structured around goal
  priority order. Claims "India's first tool to set practical goals."
  Holds SEBI registration (No. 6877, valid Dec 2025–Dec 2030).
- "Priority-based allocation" means ordered funding: fund goal 1 fully,
  then goal 2, etc. When sum of required SIPs exceeds income capacity,
  lower-priority goals simply don't get funded — not solved, just silently
  deferred. No Monte Carlo.
- Gap: priority ordering is not constraint optimization. No trade-off
  surfacing, no income trajectory, no goal probability.

**calcwise.finance** — closest match to this spec
- Features confirmed from published methodology: Monte Carlo with 1,000
  scenarios, inflation-adjusted goals, age-based asset allocation,
  multi-goal with priority tiers, feasibility status, PDF export.
  All client-side (browser session only — close the tab, everything gone).
- Confirmed gaps:
  1. No persistence. No saved plans, no cross-session comparison.
  2. Priority ordering ≠ constraint optimization. Infeasibility is not
     resolved — lower goals simply fail without explanation of what
     trade-off would make them feasible.
  3. No income trajectory. Salary is a static input; no career breaks,
     job switches, or windfall events.
  4. No goal existence probability. Every goal is treated as certain.
  5. Static allocation formula: (100 − age) ± risk adjustment. One formula
     applies to all goals regardless of timeline. A housing goal 5 years
     out and a retirement goal 40 years out get the same age-based
     allocation, not goal-specific glide paths.
  6. No cross-goal interaction. Goals are computed in isolation; over-
     committing to an early goal does not reduce what is available for
     later goals in the model.

**freefincal**
- Most technically rigorous free tool: cash-flow projection combining
  retirement with six other non-recurring goals and four recurring goals.
  Unified-portfolio approach with explicit sequence-of-returns risk
  handling. Recommends goal-specific corpus segregation as an option.
- Distributed as Excel / Google Sheets. Zero UX, fully manual, no
  interactive optimization. The methodology, not the product.
- Gap: correct math, unusable interface. A well-executed product built on
  the same methodology would directly address what freefincal's audience
  wants but cannot get in a usable form.

**SimpliFin.ai**
- B2B2C white-label engine for MFDs/RIAs. MF infrastructure SDK/APIs,
  AI-assisted goal planning, ONDC-registered Technology Service Provider.
  Raised $149K seed in 2024. First mover in ONDC-enabled MF distribution.
- Not a B2C competitor — it is the B2B2C distribution playbook already in
  market. Worth tracking as a potential V2 partnership/licensing target.

### 1.2 What is actually unclaimed

The calculator itself (single-goal SIP sizing, basic inflation adjustment)
is fully commoditized. The space that remains genuinely open:

| Differentiator | Evidence it is unclaimed |
|---|---|
| Persistent named scenarios with cross-session comparison | calcwise is session-only; no other tool in this tier offers it |
| Cross-goal constrained allocation with explicit trade-off surfacing | Recipe does ordering; calcwise does ordering; no solver exists in this market |
| Income trajectory modeling (career breaks, salary steps) | No competitor models this |
| Goal existence probability (optional/uncertain goals) | Unclaimed across all products reviewed |
| Goal-specific equity glide paths | calcwise uses one static age formula for all goals |

Monte Carlo simulation itself is table stakes (calcwise already ships it).
It is a prerequisite, not a differentiator.

### 1.3 Inflation rate reality check

The brief's education inflation range of 8–12% is confirmed but needs
sub-category precision. Official CPI education series (3.15% as of
April 2026) captures government-controlled tuition — not useful for
planning. Verified rates from fee data and published research:

| Category | Rate | Source basis |
|---|---|---|
| Education — private professional (BTech, MBBS, MBA India) | 10–15% | VIT BTech +12.3%; MBBS private +10%; MBA IIM-tier CAGR ~9–10% since 2010 |
| Education — overseas (USD/GBP-denominated) | 12–15% | Fee inflation plus INR depreciation component |
| General CPI / lifestyle | 5–6% | Long-run; recent reading 3.21% under recalibrated basket — do not silently splice series |
| Healthcare | 8–10% | Consistent across sources |
| Real estate | 7–10% city-dependent | Delhi-NCR/Mumbai skew higher; Tier-2 cities lower |
| Wedding / lifestyle events | 8–10% default | One reported spike year of 25–30% is a point outlier, not a stable CAGR — flag it as volatile, do not hardcode it |

---

## 2. Regulatory Line

### 2.1 Current SEBI IA framework (updated 2025)

SEBI eased Investment Adviser registration in 2025:
- Any graduate degree from a recognized university (finance background no
  longer required)
- NISM certification mandatory, renewal every three years
- December 2024 amendment: net-worth requirement replaced by deposit under
  lien with IAASB/BSE (minimum approximately ₹4.25 lakh)
- Client cap raised from 150 to 300 before mandatory transition to
  non-individual IA structure
- These are lower barriers than before, but still real registration — not
  a feature flag

### 2.2 The line in practice

| Output | Status |
|---|---|
| "You need to save ₹18,400/month to hit this goal at 85% probability" | Safe — math, not advice |
| "60% equity / 40% debt for a 10-year goal horizon" (asset class, not fund) | Safe — generic category-level guidance |
| "Increase equity allocation to 80% for this goal given your age and risk profile" | Gray — personalized asset allocation advice; builds toward IA trigger |
| "Invest ₹8,000/month in Mirae Asset Emerging Bluechip Fund" | Not safe — named product = IA registration required |
| "Here is a fund matching this goal's horizon" with a hyperlink | Not safe — regardless of framing |

Build to the strictest plausible reading for MVP. ET Money and Scripbox
appear to cross into recommendation territory — they hold MFD or IA
registration. Do not assume their behavior sets the permissible floor.

### 2.3 Practical path without registration

Ship MVP with:
- Zero named-product recommendations
- Asset-class guidance only (equity/debt/gold split)
- Prominent disclaimer on every output surface:
  "This is a mathematical projection, not investment advice. Consult a
  SEBI-registered Investment Adviser before making financial decisions."

V2 monetization without full IA registration: become a registered Mutual
Fund Distributor (commission-based, lighter compliance) or white-label
the calculation engine to an entity that already holds IA registration
(SimpliFin model). Neither requires full IA registration.

---

## 3. Data Model

PostgreSQL. Schema-level — no implementation code here.

### 3.1 users

```
user_id           UUID        PK
age               integer
monthly_take_home numeric(12,2)   -- current, in ₹
risk_profile      enum(conservative, moderate, aggressive)
created_at        timestamptz
```

### 3.2 income_segments

Models salary trajectory as a step function. Enables career breaks, job
switches, maternity/sabbatical, freelance periods, RSU/windfall events.

```
segment_id        UUID        PK
user_id           UUID        FK → users
from_year         integer     -- calendar year this segment starts
to_year           integer     -- null = open-ended
monthly_amount    numeric(12,2)
annual_growth_pct numeric(5,2)    -- compounding rate within this segment
segment_type      enum(salary, break, windfall, freelance)
```

A single salary + growth rate is one row with to_year = null. Career break
is a row with monthly_amount = 0. This covers both the simple case and the
full trajectory without a schema change.

### 3.3 goals

```
goal_id           UUID        PK
user_id           UUID        FK → users
label             text        -- user's name for the goal
category          enum(education_self, education_child, marriage,
                       housing, healthcare, retirement, custom)
today_cost        numeric(14,2)   -- in today's rupees
target_year       integer
confidence_pct    integer     -- 0–100; probability this goal actually happens
inflation_rate    numeric(5,2)    -- category default or user override
existing_corpus   numeric(14,2)   -- already saved toward this goal
priority          integer     -- user-set ordering; feeds optimizer weight
flexibility       enum(fixed, shiftable, reduceable)
  -- fixed: optimizer cannot touch timing or size
  -- shiftable: optimizer may delay by up to max_shift_years
  -- reduceable: optimizer may reduce target by up to max_reduce_pct
max_shift_years   integer     -- populated when flexibility = shiftable
max_reduce_pct    numeric(5,2)    -- populated when flexibility = reduceable
created_at        timestamptz
```

### 3.4 simulation_configs

```
config_id         UUID        PK
user_id           UUID        FK → users
n_simulations     integer     -- default 1000
equity_mean_pct   numeric(5,2)    -- default ~12% (Nifty 50 long-run; see §4.3)
equity_std_pct    numeric(5,2)    -- default ~18% (historical; higher than calculators assume)
debt_mean_pct     numeric(5,2)    -- default ~7%
debt_std_pct      numeric(5,2)    -- default ~3%
eq_debt_corr      numeric(4,3)    -- default ~-0.15 (mild negative historically)
glide_path_enabled boolean    -- auto-reduce equity in 5-year pre-goal window
created_at        timestamptz
```

### 3.5 simulation_runs

```
run_id            UUID        PK
user_id           UUID        FK → users
config_snapshot   jsonb       -- frozen copy of config at run time; no FK dependency
                              -- enables comparing runs across config changes
status            enum(pending, running, complete, failed)
label             text        -- e.g. "Plan A — delay marriage by 2 years"
created_at        timestamptz
completed_at      timestamptz
```

### 3.6 goal_results

One row per (run × goal).

```
result_id         UUID        PK
run_id            UUID        FK → simulation_runs
goal_id           UUID        FK → goals
future_cost_p50   numeric(14,2)   -- inflation-adjusted median future cost
future_cost_p95   numeric(14,2)   -- 95th percentile (accounts for cost uncertainty)
success_prob_pct  numeric(5,2)    -- % of simulations where corpus ≥ future cost
required_sip_p50  numeric(12,2)   -- monthly SIP for 50% success probability
required_sip_p80  numeric(12,2)   -- monthly SIP for 80% success probability
shortfall_p25     numeric(14,2)   -- corpus shortfall at 25th-percentile outcome
equity_start_pct  numeric(5,2)    -- starting equity allocation for this goal
equity_end_pct    numeric(5,2)    -- equity allocation at target year after glide
confidence_weight numeric(5,4)    -- goals.confidence_pct / 100; used in optimizer
```

### 3.7 allocation_plans

Cross-goal optimizer output per run. One row per run.

```
plan_id           UUID        PK
run_id            UUID        FK → simulation_runs
monthly_capacity  numeric(12,2)   -- investable income at run time
monthly_allocated numeric(12,2)   -- sum actually allocated across goals
feasibility       enum(fully_feasible, partially_feasible, infeasible)
```

### 3.8 goal_allocations

Per-goal slice of an allocation_plan.

```
allocation_id     UUID        PK
plan_id           UUID        FK → allocation_plans
goal_id           UUID        FK → goals
monthly_sip       numeric(12,2)
achieved_prob_pct numeric(5,2)    -- success probability under this allocation
```

### 3.9 tradeoff_suggestions

Actionable alternatives generated when the plan is partially feasible or
infeasible. Multiple rows per plan_id.

```
suggestion_id     UUID        PK
plan_id           UUID        FK → allocation_plans
goal_id           UUID        FK → goals     -- which goal this applies to
type              enum(delay_years, reduce_target_pct,
                       increase_contribution, defer_goal)
value             numeric(10,2)   -- years of delay / % reduction / ₹ increase
new_success_prob  numeric(5,2)    -- success probability if this trade-off is applied
monthly_freed     numeric(12,2)   -- ₹/month freed for other goals if applied
tradeoff_rank     integer     -- suggestions ordered by impact within a goal
```

---

## 4. Calculation and Simulation Architecture

### 4.1 Where the math runs — decision

**Server-side Python, async, with a thin client-side pre-estimate layer.**

| Layer | What it does | Why |
|---|---|---|
| Client-side pre-estimate (TypeScript, Web Worker) | 100-simulation quick run on slider change; instant feedback | Responsiveness; purely illustrative, never persisted |
| Server-side full run (Python/numpy, async job) | 1,000 simulations × N goals + constraint solver | Persistence, PDF, cross-session comparison; constraint solver cannot run in a browser |

The cross-goal optimizer is the primary differentiator. It requires
scipy.optimize and iterative Monte Carlo feedback loops that are not
feasible client-side. The client layer is a UX affordance, not the model.

### 4.2 Monte Carlo engine — structure

Annual simulation (not monthly — monthly precision is noise for 20–40 year
horizons and 12× slower). Vectorized with numpy; no Python loops in the
hot path.

```python
# annual_returns: shape (n_sims, n_years, 2) — [equity, debt] per year
annual_returns = rng.multivariate_normal(
    mean=[equity_mean, debt_mean],
    cov=[[equity_var, cov_ed], [cov_ed, debt_var]],
    size=(n_sims, n_years)
)

# Glide path: equity_weight declines linearly from eq_start to eq_end
# in the 5-year window before the goal's target year
equity_weights = build_glide_path(eq_start, eq_end, target_year, n_years)

# Blended portfolio return per simulation per year
blended = (annual_returns[:, :, 0] * equity_weights
         + annual_returns[:, :, 1] * (1 - equity_weights))

# Corpus accumulation under SIP contributions
corpus = accumulate_corpus(monthly_sip, blended, existing_corpus)

# Success probability
success_prob = (corpus >= future_cost).mean()
```

Expected runtime: under 200ms for 1,000 simulations × 40 years × 10 goals
on a single CPU core with numpy vectorization. No GPU required.

### 4.3 Return distribution parameters

Default parameters should come from actual historical data, not assumed
values. Provisional defaults pending source confirmation (see open question
6):

- Equity (Nifty 50): mean ~12%, std ~18% (std is higher than the "12%
  average" used in most calculators — wider probability bands are more
  honest)
- Debt (Crisil Composite Bond Index): mean ~7%, std ~3%
- Equity/debt correlation: ~-0.15 (mild negative, historically)

freefincal's analysis of Nifty 50 rolling 1-year returns since 2000
suggests mean closer to 14% and std ~25%. The choice matters — confirm
source before hardcoding.

### 4.4 Cross-goal allocation solver — two-stage

**Stage 1 — per-goal pass:**
For each goal independently, sweep monthly SIP values and find the SIP
that achieves the target success probability (e.g., 80%). Store as
`required_sip[goal_id]`.

**Stage 2 — constraint check and optimization:**

If `sum(required_sip) ≤ monthly_investable_capacity`: fully feasible, done.

If not, solve the weighted allocation problem:

```
maximize  Σⱼ wⱼ · pⱼ(sipⱼ)
subject to  Σⱼ sipⱼ ≤ monthly_capacity
            sipⱼ ≥ 0  for all j

where wⱼ = priority_weight[j] × confidence_pct[j] / 100
      pⱼ(sip) = success probability function for goal j
```

`pⱼ(sip)` is non-linear. For MVP: approximate it as piecewise linear from
5 Monte Carlo sample points per goal, then use `scipy.linprog` for the
relaxation. Fast enough for synchronous resolution after the MC pass.

**Stage 3 — trade-off generation:**
For each under-funded goal (achieved probability < target), compute the
three cheapest interventions and rank by monthly income freed:

1. Delay by 1–5 years — re-run MC with extended horizon; lower required SIP
2. Reduce target by 10–25% — lower future cost
3. Increase contribution — how much monthly income increase closes the gap

Surface top 3 per goal, stored in `tradeoff_suggestions`.

### 4.5 Technology stack

```
Frontend        Next.js 14 (App Router) + TypeScript
                React for interactive goal builder and sliders
                Recharts or D3 for probability fan charts
                Web Worker for 100-sim client-side pre-estimate

Backend API     FastAPI (Python 3.12)
                Pydantic v2 for request/response contracts
                Async endpoints
                BackgroundTasks for simulation jobs (MVP)
                → Celery + Redis when concurrent load demands it

Simulation      numpy, scipy (linprog, interpolate)
                Isolated as a pure Python module — no HTTP dependencies
                Testable without the full API stack

Database        PostgreSQL 16
                SQLAlchemy 2.0 (async)
                Alembic for migrations

PDF export      WeasyPrint (server-side rendering)
                Not client-side jsPDF — server-generated PDFs are
                reproducible from stored run data

Auth            Supabase Auth or NextAuth.js
                Defer if personal tool; add email/password from day 1
                if multi-user

Deployment      Vercel (Next.js frontend)
                Railway or Render (FastAPI + PostgreSQL)
                No infrastructure operations required at MVP scale
```

---

## 5. MVP vs V2 Scope

### 5.1 MVP — safe without SEBI IA registration

**Goal definition**
- N goals per user, each with: category, label, today's cost, target year,
  confidence percentage (0–100), priority, flexibility enum
- Category-specific inflation defaults (labeled as approximate and
  adjustable by the user — never presented as ground truth):
  - Education, private professional (BTech/MBBS/MBA in India): 10–12%
  - Education, overseas (USD/GBP denominated): 12–15%
  - General CPI / lifestyle: 5–6%
  - Healthcare: 8–10%
  - Real estate: 7–10% with a city selector (metro vs. Tier-2 adjusts
    the default within this range)
  - Wedding: 8–10% with an explicit UI note that a 25–30% spike was
    observed in one recent year; this default excludes that as a point
    outlier and should be treated as volatile

**Income trajectory**
- Current monthly take-home and annual growth rate (minimum viable)
- At least one career-break slot: year range, income drops to zero or
  a specified reduced amount
- Full multi-segment trajectory (job switches, freelance, windfalls) is
  in schema from day 1; UI can expose it incrementally

**Simulation**
- 1,000 simulations, server-side, vectorized
- Success probability as primary output — not a single projected number
- Probability fan chart showing P25 / P50 / P75 / P90 corpus trajectories
  per goal over time
- Goal-specific equity glide paths (not one age-based formula)

**Cross-goal optimization**
- Constrained allocation solver when sum of required SIPs exceeds capacity
- Explicit trade-off surfacing: delay goal X by N years, reduce goal Y's
  target by Z%, or increase contribution by ₹W/month
- Each trade-off shows its impact on success probability and how much
  monthly capacity it frees for other goals
- This is the primary differentiator over all existing products

**Goal probability**
- Mark any goal as optional (confidence < 100%)
- Show plan variants: "if this goal happens" vs. "if it doesn't"
- Confidence weight feeds into optimizer — uncertain goals yield less
  optimizer weight automatically

**Asset-class guidance**
- Equity/debt split recommendation per goal by horizon and risk profile
- No named products, no fund names, no bank names
- Prominent disclaimer on every output page:
  "This is a mathematical projection, not investment advice. Consult a
  SEBI-registered Investment Adviser before making financial decisions."

**Persistence and scenarios**
- Saved, named simulation runs ("Plan A — delay marriage 2 years")
- Side-by-side comparison of two saved runs
- PDF export generated server-side from stored run data (reproducible)

**Deliberately out of scope for MVP**
- Named mutual fund or bank product recommendations
- Portfolio integration with actual holdings
- Rebalancing alerts
- Any output a reasonable user would read as "buy this"

### 5.2 V2 — requires MFD registration minimum, IA for personalised advice

- Named mutual fund matching ("funds consistent with your horizon and risk
  profile" still triggers IA line; get the registration first)
- Portfolio integration via CAMS / KFintech registrar APIs
- Rebalancing alerts against a saved allocation plan
- Tax optimization across goal instruments (ELSS vs. NPS vs. ULIP
  trade-offs per goal)
- ONDC-based transaction execution (requires BSE/NSE MF infrastructure
  onboarding — not trivial)
- White-label calculation engine API for RIAs and AMCs (B2B2C, SimpliFin
  model — licenses the engine to entities that hold the required licenses)

---

## 6. Open Questions

Answer these before any code is written. Listed in priority order.

**1. Who is the user?**
Just you personally, a closed group of known people, or a public product
targeting strangers? This determines: whether SEBI compliance is relevant
for MVP at all (personal tool → not regulated), whether auth and multi-
tenancy need to be day-1 features, and what the disclaimer needs to say.
The architecture above supports all three cases, but the right MVP scope
depends on the answer.

**2. New repo, clean slate?**
The working directory appears empty or near-empty. Confirm nothing needs
to be preserved before scaffolding starts.

**3. All-in-JavaScript vs. Python backend?**
The two-service approach (Next.js + FastAPI) is the correct engineering
choice for Monte Carlo at scale and is required for the constraint solver.
But it means two services to deploy and maintain. A pure Next.js app
running simulation in a TypeScript Web Worker reaches something usable
faster but permanently caps what the solver can do — the LP optimizer and
iterative MC feedback loop are not viable client-side. Pick based on how
much of the cross-goal optimizer (the differentiator) you want in MVP.

**4. Deployment target and operational tolerance?**
Vercel + Railway is zero-ops for this scale and costs roughly $5–10/month.
If self-hosted, the stack changes. Confirm before choosing whether
BackgroundTasks or Celery is the right job runner.

**5. Unified portfolio or per-goal corpus segregation?**
Scripbox moved to one unified pool (single SIP, one portfolio, fewer
accounts). freefincal recommends per-goal segregation to control sequence-
of-returns risk on near-term goals. The data model above assumes per-goal
corpus tracking. Which model do you want, and do you want to expose the
trade-off to users?

**6. Historical return distribution source?**
Monte Carlo parameters should come from actual data, not blog-post
assumptions. Candidates:
- Nifty 50 rolling annual returns from NSE data portal (free, primary)
- Crisil Composite Bond Index for debt
- freefincal's published analysis (mean ~14%, std ~25% for Nifty 50 since
  2000 — notably higher std than the "12% average, 18% std" defaults above)
The choice materially affects how wide the probability bands are — and
wider, more honest bands are a legitimate differentiator over calculators
that show a single optimistic number. Confirm source before hardcoding
defaults.

**7. Income trajectory granularity for MVP?**
The schema supports full multi-segment income. Minimum viable: one monthly
amount plus one annual growth rate. Full version: a list of segments
covering job switches, breaks, and windfalls. Which to expose in the MVP
UI, knowing the schema already supports both?
