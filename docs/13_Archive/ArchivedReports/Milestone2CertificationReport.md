# Milestone 2 Certification Report

**Date:** 2026-07-07
**Subject:** Production-readiness certification of Milestone 2 (Family Financial Planning), Tasks 1–12, following the pre-implementation Stabilization Sprint and this session's Tasks 9–12.
**Method:** Read every governing document (`PROJECT_STATE.md`, `docs/ENGINEERING_CONSTITUTION.md`, `docs/PRODUCT_PRINCIPLES.md`, `docs/UX_PRINCIPLES.md`, `ArchitectureDecisionRecord.md`, the pre-Task-5 audit baseline — `MilestoneResumptionCertification.md` and its five companion reports — and every `*_Task9.md`–`*_Task12.md` review); direct code verification via grep/read against current `backend/app/` and `code/src/` (not assumption); a live, browser-driven end-to-end walkthrough with a fresh test account against the real running backend and Postgres; full backend test suite execution. No code was changed as part of this certification.
**Note on scope:** ~70 root-level `.md` files (e.g. `AIArchitectureReport.md`, `CompetitorAnalysisReport.md`) are pre-implementation research documents (dated 2026-07-06, never committed to git) from an earlier planning phase. They fed into `Milestone2ImplementationContract.md`, which this certification treats as the synthesized source of truth, rather than re-reading all ~70 individually — flagged under Documentation below.

---

## Overall Grade: B+ (Certified With Conditions)

Milestone 2 is architecturally sound, well-tested, and financially correct in every calculation path this audit traced. It is not blocked by any critical defect. It is held to **CERTIFIED WITH CONDITIONS** rather than an unconditional pass because of one confirmed, live-reproduced, user-visible trust bug (Risk Profile silently fails to save) that predates this session, was explicitly flagged and never fixed across 8 tasks, and directly contradicts this project's own Honesty-over-Polish principle — plus one real, scoped Product Principle gap (the Government Schemes screen was never built; its "Potentially Eligible" bucket has zero UI surface anywhere in the product).

---

## 1. Architecture

**PASS**, with the pre-existing clean baseline (`ArchitectureDriftReview.md`, run just before Task 5) re-verified against the actual Tasks 9–12 implementation:

- **Router thinness:** every endpoint in `routers/family.py` and `routers/goals.py` calls exactly one service function and returns a schema — verified for all 15 Family routes and the `family-tags` goal route. No business logic in a router body.
- **No duplicate services/calculations:** `calculate_goal_probability` has exactly two call sites (`routers/goals.py:45,92`), both legitimate (create, update-when-Calculation-Context-changes); no Task 9–12 file imports or calls it. `family_insurance_service.uncovered_parents()` — extracted in Task 12 specifically so the Parents card and the insurance recommendation share one authority — is confirmed as the only implementation of "which parents are uncovered"; nothing recomputes it independently.
- **No duplicate APIs:** full route inventory across all 7 routers shows no near-duplicate endpoint.
- **No deprecated consumers:** zero remaining frontend reads of `marital_status`/`financial_assumptions.tax_rate`; the two matches for `.dependents` in Task 12's new code are the new, distinct `FamilyDashboard.dependents` card — a naming coincidence with the deprecated `user_profiles.dependents` field, not a violation (confirmed structurally distinct).
- **No broken ownership model:** every new endpoint (`GET /family/recommendations`, `GET /family/dashboard`, `PUT /goals/{id}/family-tags`, both insurance-policy write endpoints) resolves via `get_or_create_household`/`current_user.id`-scoped queries. `get_policy()` correctly filters by `primary_holder_user_id == user.id` — no IDOR path found.
- **Calculation Lifecycle (ADR-001) integrity:** `planning_service.get_dashboard()` contains zero write operations (confirmed by reading the full function — no `db.add`/`delete`/`commit`/`flush`). The two forward-looking narrowing fixes the pre-Task-5 audit flagged (Task 8's tagging endpoint must not trigger recompute; Task 9's `update_goal()` must narrow its trigger to `CALCULATION_CONTEXT_FIELDS`) are both **confirmed correctly implemented** in current code.
- **Documentation sprawl (minor finding):** ~70 untracked root `.md` files from an earlier research phase are not load-bearing for the actual engineering record (`PROJECT_STATE.md`, `CHANGELOG.md`) — recommend archiving them out of the repo root before this milestone is considered fully "clean," since their generic names (`ExecutiveSummary.md`, `RiskChecklist.md`) invite confusion with the real audit trail.

---

## 2. Backend

**PASS.** `ruff check app/` and `mypy --strict app/` both clean across all 58 source files. 317 tests passing, 97.50% coverage (`family_dashboard_service.py`, `family_recommendations_service.py` at 100%). Every Task 9–12 service follows the established thin-router/service-owns-logic pattern. Pydantic schemas on the newest modules (`insurance.py`, `family_dashboard.py`) carry proper `Field` bounds (`gt=0`, `le=<max>`, `max_length`, `min_length`) consistent with the codebase's existing convention.

**One real inconsistency found:** `family_service.py` writes an `AuditLog` entry on member create/update/remove and goal-tag replacement (5 call sites) — but `family_insurance_service.py`'s policy create/coverage-update endpoints do **not** audit-log, breaking the pattern every other Family write establishes. Not a security hole (ownership is still correctly enforced), but a real audit-trail gap for financial-instrument records specifically. **Recommend fixing before GA**, low effort (mirror the existing `AuditLog(...)` pattern).

---

## 3. Frontend

**PASS.** `tsc --noEmit` and `eslint` clean across every touched file this session. TanStack Query used consistently with reasonable `staleTime` (30–60s) across Family/Dashboard screens, avoiding refetch storms on navigation between related screens.

**One consistency gap:** `focus-visible:` ring styling is present throughout Task 12's new dashboard section (8 instances) and the original Family Home cards, but **absent from Task 10/11's screens** (`app.family.insurance.tsx`, `app.family.recommendations.tsx` — 0 instances each despite multiple `<Link>`/`<button>` elements: "Back to Family," "Try again," "Edit coverage," form submit buttons). A keyboard-only user tabbing through the Insurance or Recommendations screens gets no visible focus indicator on these controls. **Recommend fixing before GA** — small, mechanical (add the same `focus-visible:outline-none focus-visible:ring-2...` classes already used elsewhere in the same file).

---

## 4. UX / Product Consistency

**PASS on everything built; one real, scoped gap on what wasn't.**

- Cross-surface consistency verified **live**, in this session's fresh walkthrough: the insurance recommendation read byte-identical text on `/app/family/insurance`, `/app/family/recommendations`, and the `/app/family` dashboard feed simultaneously. Adding a family member updated "Who depends on me," "Insurance coverage," and the "Parents" warning correctly and immediately.
- All 9 `PRODUCT_PRINCIPLES.md` and 11 `UX_PRINCIPLES.md` items checked against the actual shipped screens (not just the pre-Task-5 review's predictions) — no violations found in Tasks 9–12's own scope.
- **Product Principle #6 / #4 gap:** these principles require government schemes to be personalized and bucketed (Eligible / Potentially Eligible / Not Eligible), never a flat list. The Contract's Task 11 (`Milestone2ImplementationContract.md` §11) was the planned vehicle for this — but this session's Task 11 was explicitly redirected by the user to the recommendation-aggregation layer instead (documented in `DependencyValidation_Task11.md`). **Only the "Eligible" bucket now has any UI surface** (via the inline SSY callout and the Recommendations feed); "Potentially Eligible" schemes (e.g., a parent turning 60 next year, about to qualify for SCSS) have **zero visibility anywhere in the product**. `ProductConsistencyRoadmap.md`'s PCA-7 ("zero government-scheme information visible") is therefore **not fully resolved** — partially mitigated, not closed. This is a scoped product decision already surfaced to the user in `PROJECT_STATE.md`'s honest-status note, not a silent gap.
- **PCA-11 investigated and cleared:** the previously-flagged "$0 headline contradicts rising chart" finding is structurally impossible to reproduce — `NetWorthProjection`'s chart and the dashboard headline both read `dashData.net_worth`, the same value, confirmed by code. The original observation was very likely a legitimate "starting from $0, correctly projecting growth" empty-state, not a bug.
- **PCA-10/PCA-16 (unexplained jargon) confirmed still open, correctly deferred:** live-reproduced this session — a goal card shows "3.5% Monte Carlo" with zero inline explanation of what "Monte Carlo" means. Correctly out of Milestone 2 scope (owned by Milestone 6), but worth surfacing again here since it's the kind of first-impression confusion a certifying reviewer should not silently pass over.

---

## 5. Accessibility

**PASS with two gaps**, both already noted above under Frontend: missing `focus-visible` styling on Task 10/11 screens. Everywhere else: color is never the only signal (the Parents warning card states "no own insurance" in text, not just a colored border); `role="status"`/`role="alert"` correctly used for live and error content; the `<details>/<summary>` disclosure pattern is native HTML (inherently keyboard-accessible); decorative icons carry `aria-hidden="true"` consistently; checkbox fieldsets in the Add Family Member and policy-coverage forms use proper `<label>` association.

---

## 6. Security

**PASS.** No IDOR path found across any Family/Insurance/Goals endpoint — every path-param ID (`member_id`, `policy_id`, `goal_id`) is queried with a WHERE clause tying it to the authenticated user's household/user_id, not just `WHERE id = :id`. PII (member names, DOB, insurance status) is never included in the new dashboard's exception logs (`logger.exception("family_dashboard_section_failed section=%s error=%s", section, exc)` — generic identifiers only). Rate limiting applies a general per-IP bucket to all endpoints, with a stricter bucket reserved for auth/simulate — Family/Insurance writes are covered by the general limit, a reasonable two-tier design, not a gap. The one finding: **insurance-policy writes are not audit-logged** (see Backend section) — a data-completeness gap, not an access-control vulnerability.

---

## 7. Performance

**PASS for current household sizes; one real inefficiency flagged for scale.** `GET /family/dashboard` composes six independent card computations, each wrapped in its own failure-isolating `_safe()` call — a deliberate, correct resilience trade-off (Section 9 below). The cost: `list_members_with_completeness()` is queried twice per request (once for the Dependents card, once for Coverage), `list_goals_with_tags()` is queried twice (Education, Retirement), and `uncovered_parents()` runs twice (the Parents card, and again inside the recommendations feed's insurance check) — all correctness-safe (same shared function, per Task 12's own extraction), but not query-count-optimal. For today's typical household (1–5 members, 1–3 goals) this is invisible; it will matter at real scale (a household of 8 members, 15 goals). **Recommend, non-blocking:** fetch members/goals once in `get_family_dashboard()` and pass the results into each card builder, while keeping the existing per-card exception handling.

Monte Carlo cost confirmed correctly bounded: `get_dashboard()` performs zero simulation runs (ADR-001, re-verified this session); `calculate_goal_probability` is never invoked from any read path.

---

## 8. Testing

**PASS.** 317 backend tests passing, 97.50% overall coverage, 100% on the two newest aggregation services. Test suite includes the specific regression classes this milestone's own risk profile demands: calculation-lifecycle-untouched tests on every Task 9–12 read endpoint, cross-surface identity tests (`test_feed_identical_to_recommendations_endpoint`), partial-failure degradation tests (monkeypatched section/feed failures), and household-isolation tests on every new endpoint. No frontend test runner exists in this project (a standing, pre-existing gap, not introduced this session) — frontend correctness relies on `tsc`/`eslint` plus live verification, consistent with this project's established practice throughout every prior task.

---

## 9. Financial Correctness

**PASS — no incorrect financial result found anywhere in scope.**

- **Calculation Lifecycle:** probability/on_track are recomputed only on goal create or a Calculation-Context-field update; never on any read. Live-reproduced: a goal's probability was byte-identical across three separate visits and after a family-tagging action in this session's walkthrough.
- **Recommendation Engine (Insurance + Schemes aggregation):** every figure traced to a verified source — the 80D base deduction reads live from the seeded `tax_sections` table (not hardcoded); the senior-citizen 2× figure is derived structurally, never a second literal. Conflict detection is genuinely narrow (same subject **and** same `reference_code`) — verified it correctly never fires for the two current sources (SSY/child vs. SCSS/senior can't overlap on one person) rather than manufacturing a fake "always passes" test.
- **Insurance:** the recommendation is computed fresh on every read, never persisted — the `recommendations` table is confirmed at zero rows across the whole database, re-verified this session.
- **Goal Planning:** unaffected by this milestone; Monte Carlo engine itself untouched by any Task 5–12 change.
- **Government Schemes:** the eligibility engine (Task 3, pre-milestone) is correctly reused, never re-implemented, by the new aggregation layer.
- **Dashboard:** contains zero financial arithmetic of its own (verified by reading `family_dashboard_service.py` in full) — every card is a persisted value, a count, or a min-by-date selection. The one figure needing arithmetic ("months covered") is deliberately kept as frontend display arithmetic rather than a new backend calculation, per this milestone's own documented reasoning (`DependencyValidation_Task12.md` Finding 1).

**One correctness-adjacent bug, outside the calculation engine itself:** the Risk Profile field on the Profile screen — see Section 14.

---

## 10. Maintainability

**PASS.** Files stay within the project's own 200–400 line convention; the newest services (`family_dashboard_service.py`, `family_recommendations_service.py`) are single-purpose and cleanly separated. Extraction discipline was applied correctly at Task 12 (`uncovered_parents()` pulled out specifically to prevent two independent, driftable implementations) — the kind of refactor `ENGINEERING_CONSTITUTION.md` Rule 7 endorses (built for a real second caller, not speculative).

---

## 11. Documentation

**PASS for the Tasks 9–12 record itself** (every task has Dependency Validation, the relevant Integrity/Consistency reviews, live verification evidence, and a PR report); **CONCERN for the repository's overall documentation hygiene** — the ~70 untracked root `.md` files (Section 1) create real risk that a future contributor mistakes a stale research artifact for current guidance. `ArchitectureDecisionRecord.md` itself still reads "Status: Proposed — awaiting approval" at the top despite being fully implemented and verified — a stale status line, harmless but should be corrected. **Recommend:** archive the research-phase files to a `docs/archive/` or similar, and update ADR-001's status line to "Accepted — Implemented."

---

## 12. Future Compatibility

**PASS.** Re-verified `FutureCompatibilityAudit_Light.md`'s predictions against what was actually built: Task 12's composition of `get_dashboard()` materialized exactly as that report predicted (safe, cheap, no hidden recompute). No Milestone 3/4/5 assumption was invalidated by anything built this session — Milestone 4's Calculation Engine can upgrade any dashboard card's underlying figure without the dashboard changing, since it computes nothing itself; Milestone 5's Recommendation Engine can replace the feed's source service transparently.

---

## 13. Technical Debt

| Item | Status |
|---|---|
| Risk Profile field silently fails to save | **Open, confirmed live this session.** See §14. |
| Government Schemes screen (Contract §11) never built | **Open, scoped deviation.** PCA-7 partially, not fully, resolved. |
| Insurance-policy writes not audit-logged | **Open, newly identified this certification.** |
| Task 10/11 screens missing `focus-visible` styling | **Open, newly identified this certification.** |
| Family Dashboard query duplication at scale | **Open, newly identified this certification. Non-blocking today.** |
| Unexplained "Monte Carlo"/jargon terminology (PCA-10, PCA-16) | Open, correctly deferred to Milestone 6. |
| US-only account types, currency symbol, flat tax rate (PCA-4/5/6) | Open, correctly deferred to Milestone 4/localization pass. |
| "Linked accounts via Plaid" names an India-incompatible vendor (PCA-9) | Open, correctly labeled "Coming soon," blocked on a product decision. |
| `financial_assumptions.tax_rate` deprecated, no removal date | Open, documented, acceptable per Rule 11. |
| ~70 untracked root research documents | Open, documentation-hygiene only. |
| `ArchitectureDecisionRecord.md` stale "Proposed" status line | Open, cosmetic. |

**Net debt trend across this session's four tasks (9–12): flat to slightly positive** — Task 12's extraction refactor closed a potential future drift point; the newly-identified items (audit logging, focus states, query duplication) are real but individually small.

---

## 14. Known Risks

1. **Risk Profile non-persistence (confirmed, live-reproduced this session).** A user changes their risk profile on `/app/profile`, the UI displays "✓ Saved," but the value silently reverts on next load — `handleSubmit` in `code/src/routes/app.profile.tsx` only ever sends `full_name` to the API, never `riskProfile`. This was first identified during the pre-Task-5 Stabilization Sprint (`TechnicalDebtReview.md`), explicitly recommended to be filed as its own tracked bug, and was **never fixed across Tasks 5–12**. This directly violates `UX_PRINCIPLES.md` #7 (Honesty over polish — a false "Saved" confirmation) and `PRODUCT_PRINCIPLES.md` #7 (never claim capability the data model doesn't have). **This is the single highest-priority open item from this certification.**
2. **Government Schemes screen absent** — the "Potentially Eligible" bucket (a full third of the three-state design `FamilyPlanningDesign.md` Part 7 specifies) has no UI anywhere. A household with a parent about to become scheme-eligible gets no forward-looking signal today.
3. **Insurance-writes audit gap** — if this data is ever the subject of a compliance or dispute review, no audit trail exists for who created/modified a policy record, unlike every other Family write.

None of these three risks corrupt data, expose one user's data to another, or produce an incorrect financial calculation — they are trust, completeness, and auditability risks, not data-integrity or security breaches.

---

## 15. Production Readiness

Milestone 2's calculation core, data model, ownership/authorization model, and the four newest features (Family Goals tagging + custom inflation, Insurance, Recommendations, Dashboard) are production-ready as built and tested. The blocking condition is narrow and well-understood: one isolated frontend bug in Profile settings, unrelated to any Family/Calculation code shipped this milestone.

---

## FINAL DECISION

# CERTIFIED WITH CONDITIONS

**Conditions required before unconditional production certification:**

1. **Fix the Risk Profile non-persistence bug** (`code/src/routes/app.profile.tsx`'s `handleSubmit`) — send `risk_profile` to the backend, or remove the false "Saved" confirmation until it does. Small, isolated, no architecture impact.
2. **Make an explicit product decision on the Government Schemes screen** — either schedule it (closing PCA-7 fully) or formally descope it with an updated Roadmap entry, so it isn't silently forgotten a second time.

**Recommended, not blocking:**
- Audit-log insurance policy writes, matching every other Family write's existing pattern.
- Add `focus-visible` styling to Task 10/11's interactive elements.
- Reduce Family Dashboard query duplication before household sizes grow materially.
- Archive the ~70 pre-implementation research `.md` files out of the repository root; correct `ArchitectureDecisionRecord.md`'s stale status line.

Every other dimension audited — architecture, backend, financial correctness, security, testing, future compatibility — passed cleanly, verified against actual current code and a live end-to-end walkthrough, not assumption.
