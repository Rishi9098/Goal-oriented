# Monte Carlo Consistency Investigation — PCA-3

**Date:** 2026-07-07
**Scope:** Investigation only, per explicit instruction. No code changed. This finding affects financial correctness, so every claim below is traced to an exact file and line — nothing is inferred without a citation.

---

## 1. Why Is Monte Carlo Recalculated During Read Operations? — Complete Execution Path

```
GET /api/v1/dashboard  (routers/dashboard.py:14)
  └─▶ planning_service.get_dashboard(session, user)          (planning_service.py:114)
        └─▶ planning_service.refresh_goal_probabilities(session, user.id)   (planning_service.py:18)
              ├─▶ SELECT active Goal rows for this user
              ├─▶ for each goal: monte_carlo.quick_probability_async(...)   (planning_service.py:32)
              │     └─▶ monte_carlo.quick_probability(...)                  (monte_carlo.py:169→124)
              │           └─▶ monte_carlo.run_simulation(..., num_simulations=2_000, seed=None)  (monte_carlo.py:133)
              │                 └─▶ np.random.default_rng(None)             (monte_carlo.py:80)
              └─▶ goal.probability = round(prob, 1); goal.on_track = prob >= 70.0; session.add(goal)  (planning_service.py:44-46)
              └─▶ returns the (now-mutated, not-yet-committed) Goal ORM objects

GET /api/v1/reports/summary  (routers/reports.py:17)
  └─▶ planning_service.get_dashboard(session, user)   — same function, same mutation, called again independently
  └─▶ (a second SELECT for active_goals reads back the same, already-mutated-in-session objects —
       see reports.py:22's own comment: "so this costs one Monte Carlo pass, not two" — this
       comment is about avoiding a SECOND simulation within one request, not about consistency
       across separate requests to different endpoints)
```

**The mechanism, stated plainly:** `refresh_goal_probabilities()` is a function that both *reads* the current goal state and *overwrites and persists a new random result* on every call. It is invoked from two different endpoints (Dashboard, Reports), each an ordinary `GET` request with no side-effect expectation from a caller's perspective. Because `np.random.default_rng(None)` seeds from OS entropy every time (`monte_carlo.py:80`), and neither `quick_probability` nor `quick_probability_async` accept or forward a `seed` parameter at all (confirmed by their signatures, `monte_carlo.py:124-141` and `169-186` — the parameter simply does not exist on these two functions, unlike `run_simulation`/`run_simulation_async` which do), two calls one minute apart produce two different numbers for identical inputs, and the second call's result is what gets persisted and shown to whichever screen the user next opens.

## 2. Which Pages/Endpoints Trigger Recalculation — Exhaustively

Traced via `grep` for every caller of `refresh_goal_probabilities`, `get_dashboard`, and `quick_probability`/`quick_probability_async` across the entire backend:

| Trigger | Mutates & persists `Goal.probability`? | Intentional? |
|---|---|---|
| `GET /api/v1/dashboard` (Dashboard page) | **Yes** | No — a read endpoint with a write side effect |
| `GET /api/v1/reports/summary` (Reports page) | **Yes** (via the same `get_dashboard()` call) | No — same problem, second entry point |
| `GET /api/v1/goals` (Goals page) | **No** — confirmed: `list_goals()` (`routers/goals.py:37-50`) only `SELECT`s, never calls `_refresh_probability` | N/A — correctly read-only |
| `GET /api/v1/goals/{id}` | **No** — same, read-only | N/A |
| `POST /api/v1/goals` (create a goal) | **Yes**, via `_refresh_probability()` (`routers/goals.py:22-34`) | **Yes** — a new goal legitimately needs a first probability |
| `PATCH /api/v1/goals/{id}` (edit a goal) | **Yes**, same `_refresh_probability()` | **Yes** — inputs changed, a fresh number is expected |
| `POST /api/v1/simulate` | No — writes a **new** `Simulation` row (append-only history), never touches `Goal.probability` | Yes — a deliberate, separate, explicit "run a simulation" action, correctly modeled as versioned history already |
| `POST /api/v1/simulate/optimize` | No — calls `quick_probability()` repeatedly to explore contribution/risk-shift options for the *response only*; no `db.add(goal)` anywhere in `optimize()` (`routers/simulate.py:90-124`) | Yes — read-only exploration, correctly does not persist |
| Background jobs / schedulers | **None exist.** Confirmed via `grep` for `celery`, `APScheduler`, `cron`, `scheduler`, `BackgroundTasks` across the entire backend — zero matches. | N/A |

**Summary:** exactly two endpoints cause the problem (Dashboard, Reports), both via the same shared function. Every other endpoint is either correctly read-only or correctly input-triggered.

## 3. What Data Changes

- **Stored probability:** `goals.probability` (the column) — overwritten and committed on every Dashboard/Reports view, per `planning_service.py:44`.
- **Stored on-track flag:** `goals.on_track` — overwritten alongside probability (`planning_service.py:45`), derived from the same unseeded draw. This is a materially significant detail: for a goal whose true probability sits near the 70% cutoff, an unseeded re-roll can flip `on_track` between `true` and `false` on consecutive page views, changing what the Goals page's "At risk" filter shows, and changing the count of `goals_on_track` used in `alerts` (`planning_service.py:173`, `190`).
- **Cache:** none exists — there is no caching layer in front of this computation at all; every call is a fresh simulation.
- **Recommendation:** the dashboard's `suggestions` list (`_generate_suggestions`, `planning_service.py:64-111`) is generated from the just-mutated `goal.probability`/`on_track` values, so a suggestion like "Boost X — only 43% on track" can itself flicker in and out of existence across views, driven by the same noise.
- **Audit:** **nothing is logged.** Confirmed via `grep` — no `AuditLog` row is written anywhere in `planning_service.py`, `routers/dashboard.py`, or `routers/reports.py`. The overwrite is currently untraceable after the fact; there is no way to know, from the data alone, that a given `probability` value came from a passive page view rather than a deliberate goal edit.
- **Anything else:** `plan_health_score` (`compute_plan_health`, `planning_service.py:51-61`) is a weighted average of the just-mutated probabilities, so it inherits the same instability — this is the exact mechanism behind the "Plan health: 4" vs "5" discrepancy also noted in `ProductConsistencyAudit.md` PCA-12 (tied to this same root cause).

## 4. What Originally Motivated This Design — Intentional or Accidental?

Evidence points to a **partially intentional design with an accidental gap**, not a single simple mistake:

- The function is named `refresh_goal_probabilities` — "refresh" is a deliberate word choice suggesting the original intent was to keep a goal's probability current with the passage of time: `years_to_goal` is computed as `(goal.target_date - today).days / 365.25` (`planning_service.py:35`) and shrinks every single day even if the user never touches the goal. A design that recomputes on view, so the horizon used in the simulation is always "as of today," is a reasonable thing to want.
- The `reports.py:22` code comment (*"so this costs one Monte Carlo pass, not two"*) shows the original author was actively thinking about simulation **cost**, which suggests this was a considered design, not an oversight — the author appears to have optimized for "don't run it twice in one request" while not considering "don't let two different requests disagree."
- Against that: `run_simulation`/`run_simulation_async` (the full 10,000-path engine used by `/simulate`) **do** accept and correctly use a `seed` parameter, and `routers/simulate.py:53` **does** wire `settings.monte_carlo_seed` into that path. The fact that a working seeding mechanism exists in this exact codebase, and simply was never plumbed into `quick_probability`/`quick_probability_async` (the fast, 2,000-path variant used by the dashboard-refresh and goal-save paths), strongly suggests the *lack of determinism specifically* was an oversight — not a deliberate "we want fresh randomness every time" decision. No comment, docstring, or test anywhere states an intent for non-determinism; `docs/backend.md`'s own description of `MONTE_CARLO_SEED` ("Fixed RNG seed for reproducible simulations") implies the opposite intent for the codebase as a whole.

**Conclusion:** the auto-refresh-on-view *concept* was likely intentional (accounting for time decay); the *unseeded non-determinism* that makes it produce a different number every time was very likely accidental — a gap between the two "fast" functions and the one "full" function that does this correctly.

## 5. Comparison of Alternatives

| | A. Recalculate only on input change | B. Recalculate only on explicit "regenerate" | C. Async recalculation with versioning | D. Keep current behavior |
|---|---|---|---|---|
| **User trust** | High — number is stable until the user changes something real | High — most literal "nothing changes unless I ask" | High, if implemented well (single latest-version read, clear "updated X ago" timestamp) | **Lowest** — this is the bug itself |
| **Financial correctness** | Good; does not react to pure calendar drift (`years_to_goal` shrinking) between edits — a real but minor gap | Weaker than A for this product: a user could edit a goal's real inputs and see a stale number until they separately click "regenerate," which is a *worse* mismatch than A | Best long-term — full history retained, refresh cadence can be controlled deliberately (e.g. nightly) | Noise can flip `on_track` near the 70% boundary — a materially wrong signal, not just cosmetic |
| **Performance** | Best — dashboard/reports become pure reads, zero simulation cost per view | Same as A, or better | Good once built — recompute moves off the request path — but nothing today runs off the request path | Worst — every view pays a real 2,000-path × N-goals cost, repeatedly |
| **Engineering complexity** | **Lowest** — remove one function call; no new infrastructure, no schema change | Requires new explicit-trigger UI/endpoint, and removing the existing (working, reasonable) auto-refresh-on-save behavior in `goals.py` too, for consistency | **Highest** — requires background-job infrastructure this codebase does not have today (confirmed: zero scheduler/queue exists), plus versioning/staleness logic | None (already built) — but that is not a virtue given the outcome |
| **Auditability** | Good — every stored value traces to a real, identifiable user action (create/update) | Good, same as A, plus an explicit regenerate event to log | **Best** — the existing `simulations` table is already exactly this pattern (append-only, timestamped, input-snapshotted) — Option C would extend a pattern that already works elsewhere in this codebase | Worst — no record of what changed or why; nothing logged today |
| **Explainability** | High — "this is the number from when you last saved this goal" | Requires teaching users a new "regenerate" concept | Good if surfaced with a timestamp, but requires new UI work to show it | Worst — even the system itself cannot explain why the number changed, since it's RNG noise |

## 6. Recommendation

**Option A: Recalculate only when plan inputs change.**

**Justification:**
- It is the direct, minimal fix for the exact defect PCA-3 identifies: a read endpoint should not mutate stored financial data. Removing the mutation from `get_dashboard()` (called by both Dashboard and Reports) is the smallest change that eliminates the entire class of bug — no new infrastructure, no schema change, no new UI.
- The "does not react to calendar drift" trade-off is real but minor, and — critically — the *current* design does not actually deliver meaningful drift-awareness either: because the recompute is unseeded, the day-to-day change a user would see is dominated by RNG noise, not by the genuine, small effect of one fewer day remaining. Removing the recompute does not sacrifice a signal that currently works; it removes noise that was never a reliable signal to begin with.
- It directly satisfies this project's own `docs/ENGINEERING_CONSTITUTION.md` principle (implicit throughout: one calculation, one source) — after this fix, there is exactly one place a goal's probability is computed (`goals.py`'s create/update path), and every read (Goals, Dashboard, Reports) reads that same stored value with no exceptions.
- Option C is the architecturally "best" long-term answer and should be revisited during Milestone 4 (Calculation Engine) once this product actually needs scheduled, versioned recalculation (e.g., a nightly refresh job) — but building background-job infrastructure specifically to fix a stabilization-sprint Critical finding would itself be exactly the kind of scope expansion this sprint's own rules forbid ("no architecture drift," "no new features"). Option A does not foreclose Option C later; it is a correct subset of it (input-triggered recompute is the first, necessary layer C would also need).
- Option B is a worse fit for this specific product than A: it would require *removing* the already-correct, already-working create/update auto-refresh in `goals.py` and replacing it with an extra manual step, which increases friction for no corresponding benefit — Option A already gives users a stable, trustworthy number without asking them to do anything new.

**Complementary, low-risk recommendation (part of the same fix, not a separate scope item):** wire `settings.monte_carlo_seed` into `quick_probability`/`quick_probability_async` (mirroring how `routers/simulate.py:53` already does this for `run_simulation_async`), so that the one remaining legitimate trigger (goal create/update) is also reproducible when a seed is configured, and non-deterministic only when explicitly left unset — consistent with `docs/backend.md`'s own stated intent for `MONTE_CARLO_SEED`.

## 7. Exactly What Code Would Change (described only — not implemented)

- **`backend/app/services/planning_service.py`:**
  - `get_dashboard()` (line 114-115): replace the call to `refresh_goal_probabilities(session, user.id)` with a plain, read-only query for the user's active goals (the same `SELECT` `refresh_goal_probabilities` already performs internally, minus the simulation-and-overwrite step). `get_dashboard()`'s remaining logic (health score, suggestions, net worth aggregation) is unchanged — it already only *reads* `goal.probability`/`goal.on_track`, never sets them.
  - `refresh_goal_probabilities()` itself: proposed to remain in the codebase (not deleted) but no longer called from `get_dashboard()`. Its only remaining reason to exist would be if `goals.py`'s per-goal `_refresh_probability()` were refactored to reuse it for a batch case — an open question for the implementation approval step, not decided here.
  - Optionally, thread `seed=settings.monte_carlo_seed` through `quick_probability`/`quick_probability_async`'s signatures (`monte_carlo.py:124-186`) and into their `run_simulation`/`run_simulation_async` calls, and into `_refresh_probability()` (`routers/goals.py:22-34`) — the complementary recommendation above.
- **`backend/app/routers/reports.py`:** no logic change required — once `get_dashboard()` no longer mutates, the existing second `SELECT` for `active_goals` (line 27-29) is automatically consistent with `dashboard.plan_health_score`, since neither call mutates anymore. The existing code comment (line 22) would need updating since its stated rationale ("so this costs one Monte Carlo pass, not two") no longer applies — there would be zero Monte Carlo passes in this endpoint at all.
- **No other file requires a change** for Option A specifically.

## 8. Migration Impact

**None.** No schema change, no Alembic migration. `goals.probability` and `goals.on_track` are existing, already-nullable-safe (both have defaults) columns; nothing about their type, constraints, or meaning changes. This is a pure application-logic change.

## 9. Regression Risk

- **Low**, with one thing to verify explicitly during implementation: whether any existing test asserts that calling `GET /dashboard` or `GET /reports/summary` changes a goal's stored `probability`/`on_track` (i.e., a test that currently depends on the very side effect being removed). If such a test exists, it encodes the bug as expected behavior and must be corrected, not preserved — per `docs/ENGINEERING_CONSTITUTION.md` Rule 6 ("tests prove behavior; they do not get adjusted to match a bug" — here the reverse applies: a test asserting the bug's behavior is the one that's wrong).
- **No risk** to `POST`/`PATCH /goals` behavior — untouched by this change.
- **No risk** to `/simulate` or `/simulate/optimize` — untouched, different code path entirely.
- **Behavioral change users will observe:** a goal's probability and on-track status will no longer change merely by opening Dashboard or Reports. This is the entire point of the fix, not a side effect to mitigate.

## 10. Do Existing Stored Probabilities Remain Valid?

**Yes.** Every currently-stored `goals.probability`/`on_track` value is a real output of an actual 2,000-path Monte Carlo simulation — it is not corrupted or meaningless data, it simply may have been produced by a passive page view rather than a deliberate save. Under the recommended fix, these stored values require **no backfill, reset, or recomputation** as part of the fix itself: they remain exactly what they are (a valid simulation result as of whenever it was last computed) and will only change going forward when a user actually creates or edits a goal, which is the correct, intended behavior. This is a pure behavior-change-going-forward fix, not a data-correction fix.
