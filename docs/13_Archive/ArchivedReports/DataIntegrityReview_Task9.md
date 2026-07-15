# Data Integrity Review — Task 9 (Family Goals & Custom Inflation)

**Date:** 2026-07-07
**Performed before implementation**, per instruction.

## Goal ownership remains unchanged

`custom_inflation_rate` is set through the existing `PATCH /goals/{goal_id}` endpoint, which already enforces `Goal.user_id == current_user.id` before allowing any update (unchanged code path). No new ownership concept, no new authorization pattern — the field is just one more attribute of a goal the caller already owns.

## Family tags remain descriptive

Task 9 does not write to `goal_household_members` at all. The SSY-eligibility callout on the goal-detail extension *reads* existing tags (via the already-certified `GET /family/goals` and `GET /family/members/{id}`) but writes nothing — tags remain exactly what Task 8 established: a purely descriptive join, never a calculation input, never an ownership record.

## Inflation overrides affect only the intended goal

`custom_inflation_rate` is a column on the individual `Goal` row, set via `goal_id`-scoped `PATCH /goals/{goal_id}`. No batch update, no propagation to other goals, no shared/global mutation — every other goal (including other education-category goals for the same user) keeps its own independent value (`NULL` by default, meaning "use the global rate").

## Existing calculations remain deterministic

This is the central risk this review must close, and is fully addressed by the fix recorded in `CalculationContextReview.md`: `update_goal()`'s recalculation becomes conditional on the five actual Calculation Context fields being present in the PATCH body. Setting `custom_inflation_rate` alone will never invoke `calculate_goal_probability()`, so `probability`/`on_track` are guaranteed byte-identical before and after — not just "usually the same," but structurally incapable of changing from this field, regardless of RNG seeding. Verified by a permanent regression test (see Testing).

## No duplicate calculations

The future-cost projection (`current cost × (1 + rate)^years`) is a distinct, separate calculation from Monte Carlo goal-probability — it was already documented as separate in `CalculationEngineReport.md` #10/#12, and Task 9 keeps it that way: computed on-the-fly (frontend, not persisted, not backed by any new backend calculation function) from data already returned by existing, certified endpoints (`GET /goals/{id}` → `target_amount`/`target_date`/`custom_inflation_rate`; `GET /assumptions` → global `inflation_rate` fallback). No second implementation of Monte Carlo logic; no second implementation of the SSY-eligibility check (reused verbatim from Task 3/7 via `eligible_schemes`).

## No stale recommendations

No recommendation engine currently reads `custom_inflation_rate`, a goal's future-cost projection, or anything this task introduces (Milestone 5's Recommendation Engine and the Family Dashboard's recommendation feed, Task 12, are both unbuilt). Nothing exists yet that could become stale as a result of this task.
