# Calculation Context Review — Task 9 (Family Goals & Custom Inflation)

**Date:** 2026-07-07
**Performed before any code was written**, per instruction. This document answers the seven required questions with citations to the actual, current, authoritative sources — `ArchitectureDecisionRecord.md` (ADR-001), `Milestone2ImplementationContract.md` §9, `CalculationEngineReport.md` #10/#12, and the current implementation of `planning_service.calculate_goal_probability()`.

---

## Step 1 — Dependency Validation (passed, no blocker)

| Requirement | Status |
|---|---|
| Tasks 1–8 complete | ✅ Confirmed — `PROJECT_STATE.md` shows explicit "✅ Complete" headings for Tasks 5–8, each preceded by the prior task's "Stopping here" line, in order. Tasks 1–4 confirmed complete in earlier certification (`MilestoneResumptionCertification.md`). |
| Required APIs exist | ✅ `PATCH /api/v1/goals/{goal_id}` exists (`backend/app/routers/goals.py:66`). |
| Required schema exists | ✅ `goals.custom_inflation_rate FLOAT NULL` exists (migration 007, `backend/app/models/goal.py:68`). |
| Goal tagging exists | ✅ `PUT /goals/{goal_id}/family-tags` exists (Task 8, `backend/app/routers/goals.py:104`), `goal_household_members` table exists and is populated. |
| `custom_inflation_rate` exists | ✅ Confirmed on the `Goal` model. **Not yet exposed on `GoalUpdate`/`GoalResponse` schemas** — this is Task 9's own scope to add, not a blocker (the Contract's own API Contract for §9 says exactly this: "existing endpoint, extended with one new optional field"). |

No blocker. Proceeding to Step 2.

---

## Step 2 — The Seven Questions

### 1. Does changing `custom_inflation_rate` change the Calculation Context?

**No — and this is a documented, deliberate design decision, not an oversight.**

The Calculation Context, as actually implemented and documented in code today, is a closed, enumerated list — see `planning_service.calculate_goal_probability()`'s own docstring:

> "Call this only when a goal's Calculation Context — **current_amount, monthly_contribution, target_date, risk_profile, target_amount** — actually changes."

`custom_inflation_rate` is not in this list, and `Milestone2ImplementationContract.md` §9 (Performance section) explicitly and deliberately excludes it:

> "**No new calculation engine work required this milestone** beyond applying whichever inflation rate is in scope to the existing FV formula (`CalculationEngineReport.md` #10) — **the Monte Carlo re-run this would ideally trigger is a Calculation Engine milestone (4) concern; Milestone 2 surfaces the inputs, not a new simulation pipeline.**"

`CalculationEngineReport.md` #10/#12 confirm the mechanism: the "existing FV formula" is a simple, standalone compound-inflation projection —

> `future cost = Current Cost × (1 + inflation_rate)^years`

— entirely separate from the Monte Carlo `quick_probability_async` path that produces `goal.probability`/`goal.on_track`. Confirmed by reading the current engine: `calculate_goal_probability()` passes only `current_amount, monthly_contribution, years_to_goal, risk_profile, target_amount` to `quick_probability_async` — no inflation parameter exists in that function's signature at all, today.

**⚠️ This directly contradicts this task's own briefing premise** ("Changing a goal's inflation assumptions is a Calculation Context change"). See "Tension Requiring Your Decision" below — I have not resolved this unilaterally.

### 2. Should `calculate_goal_probability()` execute?

**Per the Contract: No.** Setting or changing `custom_inflation_rate` should not invoke `calculate_goal_probability()` / the Monte Carlo engine this milestone. The Contract explicitly names this exact trigger ("the Monte Carlo re-run this would ideally trigger") and explicitly defers it to Milestone 4. `goal.probability` and `goal.on_track` remain governed exclusively by the five existing Calculation Context fields, unchanged by this task.

*(If the answer to Question 1 changes per your decision below, this answer changes too — they're the same question asked two ways.)*

### 3. Should Dashboard update?

**No new content, by design.** Since `goal.probability`/`on_track` are untouched, Dashboard's plan-health score and per-goal figures are byte-identical before and after setting `custom_inflation_rate`. The Contract's Education Planning UI is scoped entirely to the goal-detail extension (§9) — the projection figure it introduces is never read by `planning_service.get_dashboard()`.

### 4. Should Reports update?

Same answer as Dashboard — no change, for the same reason. Reports reads the same stored `probability`/`on_track` fields, untouched by this task.

### 5. Should AI Copilot read the new probability automatically?

There is no "new probability" for it to read — `goal.probability` doesn't change. Not applicable.

### 6. Should recommendations be refreshed?

No recommendation engine currently reads `custom_inflation_rate` or a goal-level inflation projection (the Family Dashboard's recommendation feed, §12/Task 12, isn't built yet, and Milestone 5's full Recommendation Engine is out of scope entirely). Nothing to refresh.

### 7. Does this affect one goal or all goals?

**One goal only.** `custom_inflation_rate` is a nullable, per-goal override column (migration 007) — every other goal keeps using the global `financial_assumptions.inflation_rate` exactly as today, per the column's own additive design intent ("zero behavior change for any goal that doesn't opt in").

---

## Tension Requiring Your Decision

This task's brief states as a premise: **"Changing a goal's inflation assumptions is a Calculation Context change."** The authoritative, already-approved `Milestone2ImplementationContract.md` §9 states the opposite, with explicit reasoning: inflation is surfaced as a *display-only input* to a separate, simple FV formula this milestone, and wiring it into the Monte Carlo probability engine is explicitly named as **Milestone 4 (Calculation Engine)** scope — not Milestone 2.

I have not guessed at a resolution. Two paths, both technically buildable, produce materially different products:

- **Path A — Follow the Contract as written (recommended by the Contract itself).** `custom_inflation_rate` feeds only a new, separate, on-the-fly future-cost projection shown on the goal-detail extension (a chart + text summary: "Projected cost in N years: ₹X, using a Y% annual inflation assumption"). `goal.probability`/`on_track` are never touched by this field. No Monte Carlo change. Matches Task 9's Checklist scope exactly ("Low-Medium" complexity, 1.5 days, no calculation-engine work).
- **Path B — Treat inflation as a genuine Calculation Context field (per this task's premise).** Requires modifying `monte_carlo.py`/`quick_probability_async` to accept and apply an inflation parameter, re-deriving what "probability" even means once it's inflation-aware (real vs. nominal returns, or an inflated target_amount), and triggering recompute via the existing `PATCH /goals/{id}` path per ADR-001's trigger discipline. This is real Monte Carlo model surgery — the Contract explicitly calls this Milestone 4 work, and CLAUDE.md separately flags `monte_carlo.py` as "touch carefully."

Per this task's own Step 2 instruction — "If ADR-001 requires clarification, STOP. Do not guess" — I'm stopping here rather than silently picking one interpretation. My recommendation is **Path A**: it's what the actual, verified, already-approved Contract specifies; it keeps this task's scope matched to its own Checklist estimate; and it avoids exactly the kind of premature calculation-engine expansion this entire engagement's Stabilization Sprint was built to prevent (ADR-001 Option C was rejected for the same reason: real architecture work belongs in Milestone 4, not bolted onto a stabilization-era task).

**Awaiting your decision before proceeding to Step 3 (Data Integrity Review) or any implementation.**

---

## Decision (recorded 2026-07-07)

**Path A confirmed by the user.** Proceeding on this basis: `custom_inflation_rate` feeds only a new, separate, on-the-fly future-cost projection on the goal-detail extension. `goal.probability`/`goal.on_track` are never touched by this field; `calculate_goal_probability()` is never invoked because of it. Monte Carlo integration remains explicitly Milestone 4 scope, per the Contract.

**One additional, closely-related correctness gap surfaced during implementation planning** (not itself part of the original tension, but directly relevant to honoring Path A): `routers/goals.py`'s current `update_goal()` calls `calculate_goal_probability()` **unconditionally** after applying *any* field change — including `name`, `category`, `priority`, and (about to be added) `custom_inflation_rate`, none of which are in the documented Calculation Context. Because `settings.monte_carlo_seed` is `None` in this environment (confirmed in `config.py` and the absence of an override in `.env`), an unconditional recompute is **not a no-op** — it produces a genuinely different `probability` each time, from unseeded RNG variance, even though the actual Calculation Context inputs haven't changed. Left as-is, simply adding `custom_inflation_rate` to `GoalUpdate` would silently violate Path A the first time a user sets a custom rate: the number they see would drift, contradicting "goal.probability is never touched by this field."

**Fix, scoped narrowly to what Task 9 actually requires:** make the recalculation in `update_goal()` conditional on whether the incoming PATCH body includes at least one of the five documented Calculation Context fields (`current_amount`, `monthly_contribution`, `target_date`, `risk_profile`, `target_amount`). This is not a scope expansion — it is the literal implementation of `calculate_goal_probability()`'s own existing docstring ("Call this only when a goal's Calculation Context ... actually changes"), which the endpoint does not currently honor. Without this fix, Task 9 cannot honestly satisfy its own Data Integrity requirement ("existing calculations remain deterministic" / "tags/overrides affect presentation only").
