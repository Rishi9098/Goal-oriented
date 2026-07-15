# Implementation Checklist — Milestone 2 (Family Financial Planning)

**Date:** 2026-07-06. Strict order — each task builds on the previous; no task starts before its dependencies are merged and green, per `docs/ENGINEERING_CONSTITUTION.md`'s minimal-diff discipline and the standing instruction to never implement multiple unrelated features together.

---

### Task 1 — Migration: Milestone 2 schema additions

**Scope:** The three additive changes from `Milestone2ImplementationContract.md` §0 only — `goal_household_members` table, `goals.custom_inflation_rate`, `dependents.has_own_insurance`. Nothing else.
**Complexity:** Low. **Dependencies:** None (Foundation is certified and stable). **Estimated effort:** 0.5 day.
**Backend:** New Alembic migration (next sequential number after `006`), raw-SQL style matching every prior migration. **Frontend:** None. **Database:** The 3 changes only, verified upgrade→downgrade→upgrade against real Postgres per this project's established practice. **Testing:** Model-level tests confirming the new column/table exist and behave (nullable defaults, FK cascade). **Documentation:** `docs/database.md` new section; `PROJECT_STATE.md` entry. **Risk:** Low — purely additive, no existing table's meaning changes.

### Task 2 — Backend: Household & Member service + router

**Scope:** §2 (Family Home read), §3-7 (member CRUD: create, update, get, soft-delete), plus §1's `onboarding-seed` endpoint. One cohesive "household management" feature.
**Complexity:** Medium (the household-ownership check is a new authorization pattern for this codebase, per `APIContract.md`'s Cross-Cutting Rules). **Dependencies:** Task 1. **Estimated effort:** 2 days.
**Backend:** `app/services/family_service.py`, `app/routers/family.py`, `app/schemas/family.py` — thin router per Rule 1. **Frontend:** None yet. **Database:** Reads/writes `households`, `household_members`, `dependents` (all certified, unchanged). **Testing:** Integration tests per `TestPlan.md` §2 (household/member endpoints); the ownership-check pattern gets its own explicit cross-household-access-denied test, since it's new. **Documentation:** `docs/backend.md` new endpoints section. **Risk:** Medium — the lazy-provision fallback for pre-Milestone-2 users (§2 Acceptance Criteria) is the one piece of genuinely new logic; test it explicitly, don't assume it from the happy path.

### Task 3 — Backend: Scheme eligibility evaluation service

**Scope:** The rule-evaluation logic itself (§11's Business Rules) as a standalone, directly-testable service function — built before any UI consumes it, since both §4 (SSY inline callout) and §11 (Schemes screen) call the same function. Building it once here prevents the duplicate-logic risk `docs/ENGINEERING_CONSTITUTION.md` explicitly warns against.
**Complexity:** Medium (three rule types, the `closed_to_new` hard filter, age-boundary precision). **Dependencies:** Task 1 (household members must exist to evaluate against), certified `schemes`/`scheme_eligibility_rules` (Foundation). **Estimated effort:** 1.5 days.
**Backend:** `app/services/scheme_eligibility_service.py` — pure function(s), no router yet (routers for §4 and §11 both call this in later tasks). **Frontend:** None. **Database:** Read-only against certified Foundation tables. **Testing:** Unit tests per `TestPlan.md` §1 — every rule type, the age-boundary edge case (resolve the inclusive/exclusive-of-10th-birthday ambiguity explicitly here, in code and in a test, before any UI depends on the answer), the `closed_to_new` filter. **Documentation:** Docstring + a short section in `docs/backend.md` explaining the rule-evaluation approach and its deliberately-narrow scope (three rule types, not a general interpreter). **Risk:** Medium — this is the one piece of genuinely new business logic in the milestone; getting the age-boundary right matters because it's user-visible in two places (Add Child, Schemes screen) and wrong in either would be a real, visible correctness bug, not a cosmetic one.

### Task 4 — Frontend: Onboarding Family Step revision

**Scope:** §1 only — replace the existing onboarding family step's fields with the 3-question + count design, wired to Task 2's `onboarding-seed` endpoint.
**Complexity:** Low. **Dependencies:** Task 2. **Estimated effort:** 1 day.
**Backend:** None (already built in Task 2). **Frontend:** Modify `onboarding.tsx`'s family step component only — no other step touched. **Database:** N/A. **Testing:** UI test per `TestPlan.md` §3 (each yes/no combination); regression test confirming the other 9 onboarding steps are unaffected. **Documentation:** Update any onboarding-flow diagram in `docs/frontend.md`. **Risk:** Low, but touches a shared wizard component — regression-test the surrounding steps explicitly, not just the modified one.

### Task 5 — Frontend: Family Home screen

**Scope:** §2 only — the member-list screen, reading Task 2's `GET /family`.
**Complexity:** Low. **Dependencies:** Task 2, Task 4 (so there's seeded data to display in manual testing). **Estimated effort:** 1.5 days.
**Backend:** None. **Frontend:** New route `/app/family`, new nav item (per `FamilyPlanningDesign.md` Part 2 — including the mobile bottom-nav restructuring flagged there as a real, non-trivial change). **Database:** N/A. **Testing:** UI + accessibility tests per `TestPlan.md` §3-4. **Documentation:** `docs/frontend.md` route addition. **Risk:** Medium — the nav restructuring (demoting Reports/Profile/Settings to "More" on mobile) affects screens outside Family itself; regression-test that those routes remain reachable, not just that Family is reachable.

### Task 6 — Frontend: Add Family Member flows (Spouse / Child / Parent / Other)

**Scope:** §3-6 as one cohesive feature (shared form shell, branching by relationship type) — not four unrelated features, per this checklist's own ordering discipline.
**Complexity:** Medium (four field-set branches, the SSY inline callout wired to Task 3's service via Task 2's `PUT /members` response). **Dependencies:** Task 2, Task 3, Task 5. **Estimated effort:** 3 days.
**Backend:** None new (Task 2's endpoint already returns `eligible_schemes`). **Frontend:** Add-member form components, one per relationship type, sharing a layout shell. **Database:** N/A. **Testing:** UI tests per `TestPlan.md` §3 for all four variants; the SSY boundary edge case (`TestPlan.md` §7) explicitly. **Documentation:** None beyond what Task 5 already covers. **Risk:** Medium — this is where `UX_REVIEW.md`'s approved softened copy (gender question framing) must be implemented verbatim in intent, not re-drifted back to a more mechanical tone during implementation; a copy review against `UX_REVIEW.md` before merge is warranted.

### Task 7 — Frontend: Family Member Detail

**Scope:** §7 only.
**Complexity:** Low. **Dependencies:** Task 6 (edit re-enters those forms), Task 8 (tagged goals list — can stub with an empty state until Task 8 lands, then wire fully). **Estimated effort:** 1 day.
**Backend:** None new. **Frontend:** New route `/app/family/members/:id`. **Database:** N/A. **Testing:** UI test for Edit/Remove per `TestPlan.md` §3. **Documentation:** Route addition. **Risk:** Low.

### Task 8 — Backend + Frontend: Family Goals tagging

**Scope:** §8 only — the `family-tags` endpoint and the Family Goals screen, including the **mandatory disclosure copy** (UX_REVIEW.md revision #2, non-negotiable).
**Complexity:** Medium (new cross-ownership validation: goal ownership + household-membership on each tag). **Dependencies:** Task 1, Task 2. **Estimated effort:** 2 days.
**Backend:** Extend `app/routers/goals.py` with the new `family-tags` sub-route; extend `app/services/goal_service.py` (existing) with the tagging logic. **Frontend:** New `/app/family/goals` route; multi-select fieldset component (real checkbox group, per `UX_REVIEW.md`'s Accessibility Expert finding — not a custom chip picker). **Database:** Writes `goal_household_members` only. **Testing:** Integration + UI tests per `TestPlan.md` §2-3; **explicit test that the disclosure text renders on every tagged goal, not just once** (a real acceptance criterion, not a nice-to-have). **Documentation:** `docs/backend.md`, `docs/database.md` (usage note on the new join table). **Risk:** Medium — this is the screen `UX_REVIEW.md` flagged as the highest-trust-risk in the whole milestone; the disclosure copy is a hard requirement, not a suggestion, and should be explicitly checked in code review against the approved wording's intent.

### Task 9 — Backend + Frontend: Education Planning extension

**Scope:** §9 only — the `custom_inflation_rate` field on the existing goal-edit endpoint, plus the goal-detail extension UI.
**Complexity:** Low-Medium (the unresolved education-cost-inflation default rate flagged in the Contract — implementation must resolve this: either source and verify a specific figure, or ship with no suggested default, per `docs/ENGINEERING_CONSTITUTION.md` Rule 4). **Dependencies:** Task 1, Task 8 (goal must be tagged to know if an eligible child is attached, for the SSY-reuse callout). **Estimated effort:** 1.5 days.
**Backend:** Extend the existing `PATCH /goals/{id}` schema additively. **Frontend:** Goal-detail extension for `category='education'` goals. **Database:** Writes `goals.custom_inflation_rate` only. **Testing:** Per `TestPlan.md` §2 (existing-field regression on the extended endpoint) and §9 (figure verification, if a default rate is shipped). **Documentation:** `docs/backend.md` note on the additive schema extension. **Risk:** Medium specifically because of the unverified-inflation-rate open item — do not let this become a silently-invented number under implementation time pressure.

### Task 10 — Backend + Frontend: Family Insurance

**Scope:** §10 only.
**Complexity:** Medium (the recommendation calculation, and its dependency on `dependents.has_own_insurance` from Task 1/6). **Dependencies:** Task 1, Task 2, Task 6. **Estimated effort:** 2.5 days.
**Backend:** `app/services/family_insurance_service.py`, new routes on `app/routers/family.py`. **Frontend:** New `/app/family/insurance` route. **Database:** Reads/writes certified `health_policies`/`health_policy_coverage` (unchanged), reads Task 1's new `has_own_insurance` field. **Testing:** Per `TestPlan.md` §2, §9 (figure verification against `GovernmentPolicyReport.md`/`FamilyHUFPlanningReport.md`, exact match required). **Documentation:** `docs/backend.md`. **Risk:** Medium — a wrong deduction figure here is a financial-accuracy defect, not a cosmetic one; verify against the source report line-by-line before merge, not from memory.

### Task 11 — Frontend: Family Government Schemes screen

**Scope:** §11 only — the screen itself; the evaluation logic was already built and tested in Task 3.
**Complexity:** Low (mostly a presentation layer over Task 3's already-tested service). **Dependencies:** Task 3, Task 5. **Estimated effort:** 1.5 days.
**Backend:** One new thin route calling Task 3's service (`GET /family/schemes`). **Frontend:** New `/app/family/schemes` route, three-bucket disclosure UI. **Database:** N/A (read-only, already covered by Task 3). **Testing:** Per `TestPlan.md` §3-4 (bucketing UI, collapsed-by-default disclosure, accessibility of the `<details>`/disclosure widget). **Documentation:** Route addition. **Risk:** Low — the hard part (correctness) was de-risked in Task 3.

### Task 12 — Backend + Frontend: Family Dashboard

**Scope:** §12 only — must be last, since it aggregates every other task's output.
**Complexity:** Medium (six distinct aggregations, one of which must provably reuse rather than reimplement the existing dashboard's figures). **Dependencies:** Tasks 2, 8, 10, 11 (all must be complete and stable). **Estimated effort:** 2 days.
**Backend:** `GET /family/dashboard`, calling into `planning_service.get_dashboard()` (existing, unmodified) plus the four new services built in Tasks 2/8/10/11 — an aggregation layer, not new calculation. **Frontend:** Dashboard summary section + the existing `/app` dashboard's new Family card. **Database:** Read-only aggregation across everything above. **Testing:** Per `TestPlan.md` §2 (byte-identical figure comparison against the existing dashboard endpoint — the single most important regression check in this task), §8 (performance, no N+1 across the aggregation). **Documentation:** Final `docs/backend.md`/`docs/frontend.md` updates; this is also the natural point to update `PROJECT_STATE.md` marking Milestone 2 complete. **Risk:** Medium — the temptation to "just recompute" retirement/emergency readiness here instead of calling the existing service is the most likely place for silent logic duplication to creep in; explicitly guard against it in code review.

---

## Summary Table

| # | Task | Complexity | Effort | Depends On |
|---|---|---|---|---|
| 1 | Migration (3 schema additions) | Low | 0.5d | — |
| 2 | Household/Member service + router | Medium | 2d | 1 |
| 3 | Scheme eligibility service | Medium | 1.5d | 1 |
| 4 | Onboarding Family Step revision | Low | 1d | 2 |
| 5 | Family Home screen | Low | 1.5d | 2, 4 |
| 6 | Add Family Member flows | Medium | 3d | 2, 3, 5 |
| 7 | Family Member Detail | Low | 1d | 6, 8* |
| 8 | Family Goals tagging | Medium | 2d | 1, 2 |
| 9 | Education Planning extension | Low-Medium | 1.5d | 1, 8 |
| 10 | Family Insurance | Medium | 2.5d | 1, 2, 6 |
| 11 | Family Government Schemes screen | Low | 1.5d | 3, 5 |
| 12 | Family Dashboard | Medium | 2d | 2, 8, 10, 11 |

*Task 7 can ship with a stubbed empty "tagged goals" section before Task 8 lands, then be wired fully — noted so Task 7 isn't blocking-blocked on Task 8 unnecessarily.

**Total estimated effort: ~20.5 developer-days**, sequential per this checklist's own "one feature at a time" discipline — parallelizable in places (e.g., Task 3 and Task 4 have no dependency on each other and could run concurrently on separate branches), but never two *unrelated* features merged together in one PR.
