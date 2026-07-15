# ADR-001: Goal Probability Recalculation Trigger

**Status:** Proposed — awaiting approval. No code changed.
**Date:** 2026-07-07
**Related:** `MonteCarloConsistencyReport.md` (full investigation), `ProductConsistencyAudit.md` PCA-3, `ProductConsistencyRoadmap.md`
**Deciders:** Stabilization Sprint (this session), pending user approval

---

## Context

`ProductConsistencyAudit.md` (PCA-3, Critical) found that a goal's stored success probability changes depending on which screen the user last viewed. Root cause, fully traced in `MonteCarloConsistencyReport.md`:

`planning_service.get_dashboard()` calls `refresh_goal_probabilities()`, which re-runs a 2,000-path Monte Carlo simulation for every active goal and **persists** the new result (`goal.probability`, `goal.on_track`) — on every call. This function is invoked by two ordinary `GET` endpoints (`/dashboard`, `/reports/summary`), each with no indication to a caller that viewing them mutates stored data. Because the simulation's RNG is unseeded (`np.random.default_rng(None)`, and neither `quick_probability` nor `quick_probability_async` accept a `seed` parameter at all), each call produces a different number for identical inputs. The last screen visited wins, silently, with no audit trail.

This is a **financial correctness** issue, not merely a cosmetic one: `on_track` (a boolean derived from `probability >= 70.0`) can flip between page loads for a goal whose true probability sits near that boundary, and the dashboard's plan-health score and suggestions inherit the same instability.

## Decision

**Recalculate goal probability only when plan inputs change** (Option A in `MonteCarloConsistencyReport.md` §5) — i.e., remove the mutating call from `get_dashboard()`; the sole trigger for recomputing and persisting a goal's probability becomes the existing, already-correct create/update path in `routers/goals.py`. Dashboard and Reports become pure reads of whatever is currently stored.

As a complementary, same-fix improvement: wire `settings.monte_carlo_seed` into `quick_probability`/`quick_probability_async` (mirroring how `routers/simulate.py` already does this for the full-engine path), so the one remaining legitimate trigger is reproducible when a seed is configured.

## Alternatives Considered

| Option | Verdict |
|---|---|
| **A. Recalculate only on input change** | **Chosen.** Smallest change, no new infrastructure, directly satisfies "one calculation, one source." |
| B. Recalculate only on explicit "regenerate" | Rejected — would require *removing* the already-correct, already-working auto-refresh-on-save in `goals.py` and replacing it with a new manual step, for no corresponding benefit over A. Worse fit for this product. |
| C. Async recalculation with versioning | Rejected **for this sprint** — architecturally the strongest long-term answer (and this codebase already has the right shape for it in the `simulations` table), but requires background-job infrastructure that does not exist today (confirmed: zero scheduler/queue in the codebase). Building that now would itself be exactly the kind of architecture expansion this stabilization sprint's rules forbid. Revisit under Milestone 4 (Calculation Engine). |
| D. Keep current behavior | Rejected — this is the bug. Worst on every evaluated dimension (user trust, correctness, performance, auditability, explainability) in `MonteCarloConsistencyReport.md` §5. |

Full six-dimension comparison (user trust, financial correctness, performance, engineering complexity, auditability, explainability) is in `MonteCarloConsistencyReport.md` §5; not repeated here.

## Consequences

**Positive:**
- A goal's probability and on-track status become stable across every screen — the exact defect PCA-3 identifies is eliminated.
- Dashboard and Reports become cheaper (zero simulation cost per view instead of one 2,000-path run per active goal, per view).
- Every stored probability becomes traceable to a specific, identifiable user action (goal created or edited) — closing the current total absence of an audit trail for this data.
- No schema change, no migration, no new dependency.

**Negative / accepted trade-offs:**
- A goal's probability no longer reacts to the pure passage of time (`years_to_goal` shrinking day by day) unless the user separately edits the goal. `MonteCarloConsistencyReport.md` §4/§6 argues this trade-off is minor: the current design does not deliver a reliable time-decay signal either, since the change a user would observe today is dominated by RNG noise, not by the small, genuine effect of one fewer day remaining.
- This does not solve the underlying "should probabilities refresh periodically even without an edit" question — deferred to a future Calculation Engine milestone (Option C), where it can be built with proper versioning and background infrastructure rather than bolted onto a stabilization fix.

## Compliance with Stabilization Sprint Rules

- No new features: recomputation logic already exists (`goals.py`); this decision removes an unintended additional trigger, it does not add one.
- No architecture drift: no new infrastructure introduced.
- No calculation changes: the Monte Carlo model itself (`run_simulation`) is untouched — only *when* it is invoked and persisted changes.
- Never silently change financial behavior: this ADR and `MonteCarloConsistencyReport.md` document the decision in full before any implementation, per the sprint's Special Rule for PCA-3.

## Implementation Preview (not yet executed — requires separate approval)

See `MonteCarloConsistencyReport.md` §7 for the exact, file-by-file description of the proposed change. Summary: remove the `refresh_goal_probabilities()` call from `get_dashboard()` in favor of a plain read query; optionally thread `settings.monte_carlo_seed` through `quick_probability`/`quick_probability_async` and `_refresh_probability()`. No schema/migration change (§8). Regression risk is low, with one explicit verification item: confirm no existing test asserts the dashboard-mutates-probability behavior as expected (§9). All currently stored probabilities remain valid as-is, requiring no backfill (§10).

---

**Awaiting approval before any code is written.**
