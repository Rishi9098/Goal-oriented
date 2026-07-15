# Dependency Validation — Phase 3 (Notification Center)

**Date:** 2026-07-08
**Scope:** Verify every existing engine/data source this phase could reuse, and confirm none of them need to change.

---

## 1. Existing recommendation engine — confirmed, two independent sources, correctly never merged

`family_recommendations_service.get_family_recommendations()` is a pure **aggregation** layer — per `RecommendationConflictReview_Task11.md`, it "performs zero eligibility math and zero deduction-figure computation of its own," calling `family_insurance_service.compute_insurance_recommendation()` and `scheme_eligibility_service.evaluate_household_eligibility()` exactly as they already exist. Both are confirmed present and unchanged:
- `family_insurance_service.compute_insurance_recommendation(db, user, household) -> InsuranceRecommendation | None`
- `scheme_eligibility_service.evaluate_household_eligibility(db, household_id) -> {eligible, potentially_eligible, not_eligible}`

Per `RecommendationConsistencyReview_Task10.md`: these are **pure functions of current data, never persisted, recomputed fresh on every call, with no RNG** — verified live, repeatedly, in that report. This is the property Phase 3 must not violate: a notification's *content* must never be a stored copy of a recommendation, only a marker of whether the household has *seen* the (still freshly-computed) fact.

## 2. Existing audit logs — confirmed, and directly reusable as a notification source with zero new calculation

`AuditLog` (`user_id, action, before_state, after_state, created_at`) already records, among others:
```
family_member_added        (family_service.py:189)
family_member_updated       (family_service.py:245)
family_member_removed       (family_service.py:284)
insurance_policy_created    (family_insurance_service.py:131)
insurance_policy_coverage_updated (family_insurance_service.py:186)
```
**"Family member added" requires zero new computation** — it can be sourced directly from existing `family_member_added` rows, exactly the kind of "presentation layer only" source this phase requires.

## 3. Existing dashboard summary — confirmed stable, not a mutation risk

`planning_service.get_dashboard()` is confirmed, by direct code inspection, to be a pure read: `_active_goals()` is explicitly commented "Read-only fetch — never mutates or persists a probability." **ADR-001 is fully implemented in code**, despite its own status line still reading "Proposed" (a known, previously-flagged stale-documentation item, not a code defect) — `calculate_goal_probability()` is the single, centralized trigger, called only from `routers/goals.py`'s create/update path, never from a read path. This confirms `goal.probability` and `goal.on_track` are **stable, already-computed, already-stored values** — safe to read for a notification source without triggering a recalculation.

## 4. Existing family recommendation service, insurance recommendation service, government scheme evaluation — all confirmed present and unchanged (§1)

## 5. Existing goal probability engine — confirmed, and its stored outputs are directly reusable without recomputation

`Goal.on_track` (bool) and `Goal.probability` (float) are stored columns, updated only on create/edit (§3). Two zero-new-calculation notification conditions follow directly:
- **"Goal at risk"** = `!goal.on_track` — a read of an already-stored boolean, not a new computation.
- **"Goal completed"** = `goal.current_amount >= goal.target_amount` — a comparison of two already-stored numbers, not a new computation.

**"Goal probability *changed*"** (an explicit example in this phase's instructions) is different in kind from the two above: it requires comparing *today's* stored probability against a *previously-seen* value — state that does not exist anywhere in the schema today. Unlike "at risk" and "completed" (snapshot conditions, safely re-evaluated fresh every time), a "changed" notification needs new, persisted state to remember the last value a user was shown. **This is flagged here as requiring genuinely new state-tracking, not deferred silently** — resolved in `ArchitectureReview_Phase3.md`.

## 6. The dead `Recommendation`/`RecommendationCitation` tables — re-confirmed still completely unused

Zero import sites anywhere in `app/` outside the model file itself (re-confirmed by exhaustive grep). **This phase must not build on them** — reviving a persisted-recommendation table for notifications would recreate exactly the staleness risk Task 10's "never persisted" design was built to prevent (`NotificationCenterDesign.md` §2, written during the Global Shell Architecture Review, still holds and is not re-litigated here).

## 7. What this confirms is available, with zero new calculation, for Phase 3

| Candidate source | Computation required | New? |
|---|---|---|
| Insurance recommendation exists | None — read `compute_insurance_recommendation()`'s current output | No |
| Scheme eligibility exists | None — read `evaluate_household_eligibility()`'s current output | No |
| Family member added | None — read existing `AuditLog` rows | No |
| Goal at risk | None — read stored `goal.on_track` | No |
| Goal completed | None — read stored `current_amount`/`target_amount` | No |
| Goal probability changed | **Yes** — no "last seen" value exists anywhere | New state required |

## Conclusion

Five of the six candidate sources named in this phase's instructions are reachable with **zero new calculation** — pure reads of already-computed, already-stored, or already-logged data. The sixth ("goal probability changed") is the one source that cannot be built without new state, and is treated as a deliberately scoped decision point for Architecture Review rather than silently included or silently dropped. **No incorrect assumption found — proceeding to Architecture Review.**
