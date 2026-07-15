# Future Compatibility Audit (Light) — Post-Stabilization-Sprint Milestone 2 Review

**Date:** 2026-07-07
**Scope:** Verify that Milestone 2's remaining tasks (5-12) and their governing `Milestone2ImplementationContract.md` are still correct after the Stabilization Sprint's three fixes (PCA-1, PCA-2, PCA-3). Investigation only — no code, no documentation, no task work performed.
**Method:** Each remaining task checked against every file changed in the Stabilization Sprint (`code/src/components/onboarding/wizard-steps.tsx`, `code/src/routes/app.profile.tsx`, `code/src/lib/api.ts`, `backend/app/services/planning_service.py`, `backend/app/services/monte_carlo.py`, `backend/app/routers/goals.py`, `backend/app/routers/reports.py`, `docs/architecture.md`, `docs/backend.md`, `docs/ENGINEERING_CONSTITUTION.md`), plus a fresh read of the current `backend/app/schemas/goal.py` and `backend/app/routers/goals.py` to verify assumptions against actual code, not memory.

---

## Per-Task Review

### Task 5 — Family Home screen

1. **Still Valid?** YES.
2. **Depends on Stabilization Sprint behavior?** Yes, positively. Reads `GET /api/v1/family` — the same endpoint PCA-2 already wired a frontend client for (`api.getFamilyHome()` in `code/src/lib/api.ts`), returning exactly the `{household, members: [{id, relationship_type, name, is_complete}]}` shape the Contract's §2 API Contract specifies. Task 5 can reuse `api.getFamilyHome()` as-is — no new API client function needed, reducing this task's frontend scope slightly versus what the Contract originally assumed (a net-positive side effect of PCA-2, not a risk).
3. **References deprecated architecture?** No.
4. **Requires contract updates?** No functional change, but recommend one clarifying sentence: note that `api.getFamilyHome()` already exists (added during PCA-2) and should be reused, not reimplemented, to avoid a future contributor writing a second, duplicate client function for the same endpoint.
5. **Requires UX updates?** No blocker. One forward-looking, non-blocking opportunity: Profile's Household field (PCA-2's fix) currently reads *"This reflects the family details you've shared and can't be edited here yet."* Once Task 5 ships, that copy's "not yet" becomes literally true elsewhere in the product — a natural (not required) follow-up would be a small copy/link update on Profile pointing to the new Family screen. Not in Task 5's scope; flagged for whoever next touches Profile.
6. **Requires API updates?** No — `GET /api/v1/family` (Task 2, certified) is unchanged by the Stabilization Sprint.
7. **Requires documentation updates?** No, beyond the one clarifying sentence in #4.
8. **Requires test updates?** No.
9. **Risk level:** Low (was already Low per the Checklist; unchanged).
10. **Recommendation:** Proceed as originally scoped. Explicitly reuse `api.getFamilyHome()`.

### Task 6 — Add Family Member flows (Spouse/Child/Parent/Other)

1. **Still Valid?** YES.
2. **Depends on Stabilization Sprint behavior?** No. Writes to `household_members`/`dependents` via Task 2's existing `PUT/POST /family/members` endpoints — untouched by any of the three fixes. No interaction with `calculate_goal_probability`, deprecated fields, or the Household display.
3. **References deprecated architecture?** No.
4. **Requires contract updates?** No.
5. **Requires UX updates?** No.
6. **Requires API updates?** No.
7. **Requires documentation updates?** No.
8. **Requires test updates?** No.
9. **Risk level:** Medium (unchanged from Checklist — the SSY-callout wiring and the softened gender-question copy remain the real complexity, unrelated to this sprint).
10. **Recommendation:** Proceed as originally scoped.

### Task 7 — Family Member Detail

1. **Still Valid?** YES.
2. **Depends on Stabilization Sprint behavior?** No direct dependency. Indirectly benefits from Rule 11 (Deprecation Completion, added during PCA-2): this task's "Goals involving X" list must read `goal_household_members` joined to `goals` — a completely different table from anything deprecated, but the new Rule is a useful checklist item to apply here since it's the kind of join that could accidentally reach for a stale field if implemented carelessly.
3. **References deprecated architecture?** No.
4. **Requires contract updates?** No.
5. **Requires UX updates?** No — the confirm-dialog pattern it reuses (`GoalSimPanel.tsx`) is unrelated to any Stabilization Sprint file.
6. **Requires API updates?** No.
7. **Requires documentation updates?** No.
8. **Requires test updates?** No.
9. **Risk level:** Low (unchanged).
10. **Recommendation:** Proceed as originally scoped. Apply ENGINEERING_CONSTITUTION.md Rule 11 as a general implementation checklist item (verify no field surfaced on this screen is deprecated) — routine due diligence, not a blocker.

### Task 8 — Family Goals tagging

1. **Still Valid?** YES.
2. **Depends on Stabilization Sprint behavior?** Adjacent, not blocking. This task extends `app/routers/goals.py` — the exact file `calculate_goal_probability` was centralized into during PCA-3. The new `PUT /goals/{goal_id}/family-tags` endpoint only writes `goal_household_members` (a pure tag, per the Contract's own Business Rules) and never touches `current_amount`/`monthly_contribution`/`target_date`/`risk_profile`/`target_amount` — so it correctly should **not** call `calculate_goal_probability()` at all. Confirmed via a fresh read of the current `routers/goals.py`: the file's shape (thin router, one centralized import from `planning_service`) makes this easy to get right, but it is a new route in the same file, so implementation should explicitly confirm the new endpoint does not accidentally invoke the probability calculation — tagging is not a Calculation Context change.
3. **References deprecated architecture?** No.
4. **Requires contract updates?** One recommended clarifying note (non-blocking): state explicitly in §8 that `family-tags` must not trigger `calculate_goal_probability()` — consistent with, and citing, ADR-001. This makes the "don't touch the calculation" boundary explicit for whoever implements Task 8, rather than implicit from the Business Rules text alone.
5. **Requires UX updates?** No — the mandatory disclosure copy requirement is unrelated to any Stabilization Sprint fix.
6. **Requires API updates?** No — this is a net-new endpoint, unaffected by the sprint.
7. **Requires documentation updates?** Yes, minor: `docs/backend.md`'s new Calculation Lifecycle-adjacent description (added during PCA-3) could note, when Task 8 ships, that tagging is explicitly excluded from the Calculation Lifecycle's trigger set — a one-line addition at that time, not now.
8. **Requires test updates?** Yes, forward-looking: Task 8's own test suite should include an explicit assertion that tagging a goal does not change its `probability`/`on_track` (a direct, cheap regression guard consistent with the two new tests PCA-3 added to `test_dashboard.py`/`test_reports.py`).
9. **Risk level:** Medium (unchanged from Checklist), with one clarified reason: the new cross-ownership validation remains the main complexity; the calculation-boundary question above is a small, easily-addressed addition, not a new risk driver.
10. **Recommendation:** Proceed as originally scoped, with the one contract clarification and one test addition noted above folded into Task 8's own implementation, not treated as a prerequisite blocker.

### Task 9 — Education Planning extension

1. **Still Valid?** YES, with one genuine implementation-time interaction identified below — not a blocker, but worth resolving deliberately rather than by accident.
2. **Depends on Stabilization Sprint behavior?** **Yes, directly and materially.** Task 9 extends `PATCH /goals/{id}` with a new optional field, `custom_inflation_rate`. Verified against the current (post-PCA-3) `routers/goals.py`: `update_goal()` calls `calculate_goal_probability(goal)` **unconditionally on every PATCH**, regardless of which fields were actually sent in the request body — this was true before the Stabilization Sprint too (the old `_refresh_probability()` had the identical unconditional-call behavior), so PCA-3 did not introduce this, but PCA-3's own governing principle (ADR-001: recalculate only when the Calculation Context actually changes) throws it into sharp relief. `custom_inflation_rate` is explicitly **not** a Monte Carlo input — the Contract's own §9 Performance note says exactly this: *"the Monte Carlo re-run this would ideally trigger is a Calculation Engine milestone (4) concern; Milestone 2 surfaces the inputs, not a new simulation pipeline."* As implemented today, a user setting only `custom_inflation_rate` via `PATCH /goals/{id}` will still trigger a full, real 2,000-path Monte Carlo simulation as a side effect — wasteful, and in mild tension with the Contract's own stated intent for this field, though not a violation of PCA-3's core rule (the recompute is still write-triggered, not read-triggered).
3. **References deprecated architecture?** No.
4. **Requires contract updates?** **Yes — recommended.** Add an implementation note to §9 (or a general note near ADR-001's reference in the Contract) that `update_goal()`'s recompute trigger should be narrowed to fire only when a Calculation Context field (`current_amount`, `monthly_contribution`, `target_date`, `risk_profile`, `target_amount`) is present in the PATCH body — not on every PATCH unconditionally. This is a small, additive refinement of the same centralized function ADR-001 already established, not a new architecture.
5. **Requires UX updates?** No.
6. **Requires API updates?** No new endpoint; the recommended change is an internal trigger-condition refinement to the existing `calculate_goal_probability()` call site, invisible to the API contract itself.
7. **Requires documentation updates?** Yes: `docs/architecture.md`'s new "Calculation Lifecycle" section (added during PCA-3) should be extended, at Task 9 implementation time, to state the trigger condition precisely (which fields, not "any PATCH").
8. **Requires test updates?** Yes, forward-looking: a test asserting that a PATCH containing only `custom_inflation_rate` does not change `probability`, once the trigger is narrowed.
9. **Risk level:** **Medium** (was Low-Medium per the Checklist, for a different reason — the unverified inflation-rate figure; this finding adds a second, independent reason, so Medium is the more accurate rating going forward).
10. **Recommendation:** Proceed, but resolve the recompute-trigger question explicitly during Task 9's own Design Review step — do not let it be decided implicitly by whatever the code happens to already do. This is a small, well-understood fix (narrow one `if` condition), not a redesign, and keeps faith with ADR-001's own principle rather than quietly contradicting it in a new code path.

### Task 10 — Family Insurance

1. **Still Valid?** YES.
2. **Depends on Stabilization Sprint behavior?** No. Reads `dependents.has_own_insurance` (Task 1, certified, untouched) and `health_policies`/`health_policy_coverage` (Foundation, untouched). No interaction with Monte Carlo, deprecated fields, or the household display.
3. **References deprecated architecture?** No.
4. **Requires contract updates?** No.
5. **Requires UX updates?** No.
6. **Requires API updates?** No.
7. **Requires documentation updates?** No.
8. **Requires test updates?** No.
9. **Risk level:** Medium (unchanged — the deduction-figure verification remains the real risk, unrelated to this sprint).
10. **Recommendation:** Proceed as originally scoped.

### Task 11 — Family Government Schemes screen

1. **Still Valid?** YES.
2. **Depends on Stabilization Sprint behavior?** No. Pure presentation layer over Task 3's already-certified, read-only `scheme_eligibility_service` — untouched by any of the three fixes.
3. **References deprecated architecture?** No.
4. **Requires contract updates?** No.
5. **Requires UX updates?** No.
6. **Requires API updates?** No.
7. **Requires documentation updates?** No.
8. **Requires test updates?** No.
9. **Risk level:** Low (unchanged).
10. **Recommendation:** Proceed as originally scoped.

### Task 12 — Family Dashboard

1. **Still Valid?** YES — and materially **strengthened** by PCA-3, not just unaffected.
2. **Depends on Stabilization Sprint behavior?** **Yes, directly and positively.** The Contract's own §12 Business Rules already state "Retirement readiness (existing `plan_health_score`-adjacent figure, **reused, not recalculated**)" and the Performance section already says this endpoint should "reuse existing dashboard computation rather than duplicating it." Before PCA-3, calling `planning_service.get_dashboard()` from within a new family-dashboard aggregation would have silently triggered a full batch Monte Carlo recompute as a side effect — directly contradicting the Contract's own stated intent for this task, and adding an unbudgeted performance cost the Checklist's Task 12 risk note ("guard against N+1 across the aggregation") was implicitly worried about. After PCA-3, `get_dashboard()` is a pure, cheap read — so Task 12 can now compose it exactly as the Contract always intended, with no hidden recompute cost and no risk of a Family Dashboard page view silently mutating a goal's stored probability as a side effect of viewing an aggregation screen.
3. **References deprecated architecture?** No.
4. **Requires contract updates?** One recommended clarifying addition: note explicitly that this task's safety now also depends on `get_dashboard()` being read-only (ADR-001) — worth stating so a future reader understands *why* composing it here is safe, not just that it happens to be.
5. **Requires UX updates?** No.
6. **Requires API updates?** No.
7. **Requires documentation updates?** Yes, minor: cross-reference ADR-001 from this task's eventual `docs/backend.md` entry, for the same reason as #4.
8. **Requires test updates?** Yes, forward-looking: Task 12's own test suite should include the same kind of regression test PCA-3 added elsewhere — repeated `GET /family/dashboard` calls never change any goal's probability.
9. **Risk level:** Medium (unchanged rating, but the *nature* of the risk shifted — the N+1/hidden-recompute risk the Checklist worried about is now structurally impossible; the remaining Medium risk is purely the aggregation-correctness concern the Checklist already named).
10. **Recommendation:** Proceed as originally scoped — this task is in a better position than when the Checklist was written.

---

## Implementation Contract Review — Section-by-Section

Reviewed the entire `Milestone2ImplementationContract.md` against the five specified drift sources.

| Source of potential drift | Finding |
|---|---|
| **Household model changes** | None occurred. PCA-2 changed *how Profile displays* household data (read-only, sourced from the certified `GET /api/v1/family`); it did not change the household/member/dependent schema, the ownership-check pattern, or any Contract-specified API shape. §0-§8's household-related specs remain accurate as written. |
| **Calculation Lifecycle** | Directly affects Task 9 (see above — the recompute-trigger granularity question) and directly *benefits* Task 12 (see above — `get_dashboard()` is now provably safe to compose). No other section references Monte Carlo or `calculate_goal_probability` at all — confirmed via a full re-read of §1-§12. |
| **Product Consistency fixes** | PCA-1's fix (onboarding copy) and PCA-2's fix (Profile display) are both about *existing, already-shipped* Task 4 and Profile — neither changes anything §1-§12 of the Contract specifies for *remaining* tasks. The one soft touchpoint: Task 5, once shipped, makes the destination PCA-1's copy stopped promising real again — see Task 5's UX note above (an opportunity, not a requirement). |
| **Engineering Constitution Rule 11 (Deprecation Completion)** | No remaining task (5-12) reads or writes `user_profiles.marital_status`/`dependents` or `financial_assumptions.tax_rate` — confirmed via a full text search of the Contract's §1-§12. Rule 11 is a good general due-diligence checklist item for every remaining task (flagged generically under Task 7 above) but changes no specific Contract text. |
| **Read-only household profile** | Profile's Household field being read-only (PCA-2) does not conflict with Task 5-7's plan to make the *Family* screens fully interactive — these are different screens by design, and the Contract never specified Profile as an editing surface for household data in the first place. No conflict, no update needed beyond the Task 5 UX note. |
| **New ADR (ADR-001)** | Recommend adding one short cross-reference in the Contract's own Shared Baselines section (or a new short "Calculation Lifecycle Compliance" subsection) pointing to `ArchitectureDecisionRecord.md`, so future task implementers (Tasks 8, 9, 12 specifically) have a one-line pointer to the rule rather than needing to rediscover it from the codebase. This is a documentation convenience, not a correctness requirement — every task above was independently verified against the actual current code, not against the absence of this cross-reference. |

**Overall Contract verdict:** No section is factually outdated. Three small, additive clarifications are recommended (Task 8's tagging/calculation boundary, Task 9's recompute-trigger granularity, a general ADR-001 cross-reference) — all can be folded into each task's own Design Review step when that task is actually implemented, none require editing the Contract today as a precondition for resuming work.
