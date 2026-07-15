# Dependency Validation — Task 12 (Family Dashboard Integration)

**Date:** 2026-07-07
**Performed before any code was written**, per instruction.

## Checklist

| Requirement | Status |
|---|---|
| Tasks 1–11 complete | ✅ Confirmed via `PROJECT_STATE.md` (Task 11 approved this turn). |
| Family Recommendation Service (Task 11) | ✅ `family_recommendations_service.get_family_recommendations()` — exists, certified, 100% covered. Task 11's own PROJECT_STATE entry explicitly anticipated this task calling it directly. |
| Insurance Service (Task 10) | ✅ `family_insurance_service.list_policies_with_coverage()` (for "N of M covered") and `compute_insurance_recommendation()` — exist, certified. |
| Scheme Eligibility Service (Task 3) | ✅ Consumed indirectly via the Task 11 aggregation — the dashboard never calls it directly, avoiding a second aggregation path. |
| Goal Services (Task 8/9) | ✅ `family_service.list_goals_with_tags()` — returns every active goal with tagged members; education/retirement/emergency cards all derive from this one existing call (persisted `probability`/`on_track`/`target_date` — no recomputation). |
| Household Services (Task 2/6) | ✅ `family_service.get_or_create_household()` + `list_members_with_completeness()` — the "Who depends on me?" and "Insurance coverage" denominators. |
| Existing money dashboard | ✅ `planning_service.get_dashboard()` — documented read-only (ADR-001 comment in source, verified by reading it this task), returns `plan_health_score`, `projected_retirement`, `liquid_assets`, `monthly_expenses`. |
| `Stat`/`StatSkeleton` UI pattern | ✅ Exists in `code/src/routes/app.index.tsx` (local components — the pattern is reused, the grid markup mirrored). |

## Finding 1 — the Contract references an "emergency-fund-months calculation" that does not exist

`Milestone2ImplementationContract.md` §12 says Emergency readiness reuses "the existing emergency-fund-months calculation," and `FamilyPlanningDesign.md` Part 6's mock shows "4.2 months covered." **No such calculation exists anywhere in the codebase** — verified by grep across backend and frontend; `get_dashboard()` returns `liquid_assets` and `monthly_expenses` but no months figure, and the Reports screen has none either.

**Resolution (not a blocker — the brief's own constraints dictate the answer):** inventing a backend months calculation would violate two of this turn's explicit requirements ("No financial calculations occur during read operations", "Do not create parallel business logic"). Instead, the backend passes through `get_dashboard()`'s two authoritative figures verbatim, and the **frontend renders "X months covered" as display-level arithmetic** (`liquid_assets / monthly_expenses`, guarded for zero) — exactly the precedent Task 9 set when it deliberately kept the future-cost projection (`current_cost × (1+rate)^years`) on the frontend to keep the backend read path calculation-free. When `monthly_expenses` is 0 (no financial data entered), the card shows an honest "add your income & expenses" empty state, never a fabricated or infinite figure.

## Finding 2 — the Parents card's literal Contract condition would contradict the Recommendations feed on the same screen

The Contract defines the Parents card as "any parent-type member with `has_own_insurance != 'yes'`" — the *raw* stored answer. But Task 10 established (and live-verified) that an on-file active policy supersedes a stale `has_own_insurance` answer. If the card used the raw condition while the feed uses the guarded condition, one screen could simultaneously show "⚠ Mother: no own insurance" and *no* corresponding recommendation — exactly the self-contradiction the Contract's own Acceptance Criteria forbids ("never shows a recommendation whose source screen wouldn't independently justify it" — and by symmetry, never a warning the recommendation engine has already determined is resolved).

**Resolution (not a blocker):** extract the existing uncovered-parents determination (complete parent + `has_own_insurance != 'yes'` + not covered by an active policy) from `compute_insurance_recommendation()` into a public helper, called by **both** the recommendation and the dashboard card — single source of truth, zero duplicated logic, card and feed structurally incapable of disagreeing. This mirrors the `age_years` promotion precedent from Task 10.

## Conclusion

**No blockers.** Every service this turn's reuse list names exists and is certified. The two findings above are documented deviations with resolutions dictated by the brief's own harder constraints, not open questions — proceeding to Reviews 2–6.
