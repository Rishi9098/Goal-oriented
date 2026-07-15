# Milestone 2 Re-Certification Report (v2)

**Date:** 2026-07-08
**Scope:** Full re-certification of Milestone 2 following the Milestone 2.1 Production Stabilization Sprint.
**Predecessor:** `Milestone2CertificationReport.md` (2026-07-07) — **CERTIFIED WITH CONDITIONS**, four named conditions.
**Method:** Direct re-reading of current source code (not assumed from prior reports), fresh full-suite test runs, fresh lint/type-check sweeps, live keyboard-only and mouse-driven browser verification against the running application and real Postgres database, and a full re-read of `PROJECT_STATE.md`, all five Milestone 2.1 PR reports, all ADRs, `docs/ENGINEERING_CONSTITUTION.md`, `docs/PRODUCT_PRINCIPLES.md`, and `docs/UX_PRINCIPLES.md`.

No code was modified as part of this re-certification. This is an audit only.

---

## 0. Disposition of the Four Certification Conditions

| # | Condition (from v1) | Resolved by | Verified how |
|---|---|---|---|
| 1 | Risk Profile field on the Profile page implied a saved preference that was never persisted or used anywhere | M2.1-P0 | `grep` of `app.profile.tsx` confirms zero `riskProfile`/`RISK_OPTIONS` references (down from present in v1). Confirmed distinct from, and non-disruptive to, the legitimate per-goal `Goal.risk_profile` field (still fully wired through `monte_carlo.py`, `optimizer.py`, `planning_service.py` — untouched, as it should be). Live-verified: Profile page shows only Full Name, Email, Household. |
| 2 | Government Schemes screen did not exist (PCA-7 partially resolved) | M2.1-P1 | `code/src/routes/app.family.schemes.tsx` exists; `GET /family/schemes` endpoint confirmed in `backend/app/routers/family.py`. Live-verified: screen loads, reuses the existing three-bucket (Eligible/Potentially/Not eligible) pattern, linked from Family Home between Insurance and Recommendations. |
| 3 | Insurance policy create/update writes were not audit-logged | M2.1-P2 | `grep` of `family_insurance_service.py` confirms `insurance_policy_created` and `insurance_policy_coverage_updated` `AuditLog` writes present in `create_policy()` and `replace_policy_coverage()`. |
| 4 | Tasks 10/11's screens (and, on closer inspection, Tasks 5–8 too) lacked visible keyboard-focus indicators | M2.1 Accessibility Polish | `grep -c "focus-visible:"` across all 6 affected files shows non-zero counts everywhere previously flagged as zero. Live-verified via real Tab-key navigation on the Insurance and Recommendations screens: focus rings render correctly. |

All four conditions are resolved and independently re-verified in this audit, not merely trusted from the PR reports.

**Additional finding from the same sprint (not a v1 condition, but addressed):** Dashboard query count reduced from a measured 25 to 22 SELECT queries per `GET /family/dashboard` call, and an N+1 pattern in `list_policies_with_coverage()` was batched. Verified present in current code (`family_dashboard_service.py`'s shared-fetch comment, `family_insurance_service.py`'s `_covered_members_for_policies`).

---

## 1. Architecture Health Review

- **Routers remain thin** (`ENGINEERING_CONSTITUTION.md` Rule 1): the new `GET /family/schemes` endpoint in `family.py` is a direct passthrough to `scheme_eligibility_service.evaluate_household_eligibility()` — no business logic added to the router. Confirmed by reading the endpoint directly.
- **No new duplicated logic**: the Schemes screen reuses the existing Scheme Eligibility Service and Recommendation Aggregation Service verbatim (`DependencyValidation_M2.1-P1.md`); the audit-logging fix reuses the existing generic `AuditLog` model and the established `db.add(AuditLog(...))` post-flush pattern with zero new mechanism.
- **Failure-isolation architecture preserved**: the dashboard query optimization (M2.1-P4) was the highest-risk change to this property, and it was verified not to weaken it — a shared-fetch failure degrades exactly the same set of cards to `None` as independent per-card failures would have, confirmed by the existing partial-failure tests passing unchanged.
- **No new service coupling**: `family_recommendations_service.py` was untouched by the dashboard optimization; the one new inter-function dependency (`uncovered_parents()`'s optional `covered_ids` parameter) is backward-compatible and internal to `family_insurance_service.py`.
- **ADR-001 (Calculation Lifecycle)** remains the enforced rule — `CALCULATION_CONTEXT_FIELDS` in `planning_service.py` is unchanged by this sprint; all four M2.1 findings were read-path or write-audit changes, none touched recalculation triggers. Confirmed via the full test suite (330/330 passing, including `test_planning_service.py`'s calculation-lifecycle tests).
- **Open, non-blocking item (unchanged from v1):** `ArchitectureDecisionRecord.md`'s ADR-001 status line still reads "Proposed — awaiting approval. No code changed," despite the calculation lifecycle rule having been enforced in production code for weeks. This is a stale documentation line, not a code defect, and remains open because none of the four M2.1 findings' scopes included touching this file.

**Verdict: Passes.**

---

## 2. Product Health Review

- **Product Principle #6** ("Government schemes... personalized, never presented as long lists"): the Schemes screen's three-bucket design directly satisfies this — verified live, not a flat list.
- **Product Principle #7** ("Never claim capability the data model doesn't actually have"): this is the exact principle the Risk Profile bug violated, and the fix (removing the false capability rather than building a new backend feature to justify it) is the philosophically correct resolution per this document, not just a pragmatic one.
- **UX Principle #6** ("Users always know what to do next") and **#11** ("Empty states are normal states"): the Schemes screen's empty/zero-member state ("Not eligible — show 9 more," collapsed) was live-verified for a fresh account with no family members yet — behaves correctly, no dead end.
- **UX Principle #8** ("Color is never the only signal"): re-confirmed unaffected by this sprint — the Parents card and Schemes buckets still pair icon + text label, as established in the original Tasks 10/11.

**New, minor finding surfaced during this re-certification (not part of the four v1 conditions, not touched by any M2.1 fix):** the top navigation bar (`app-shell.tsx`) and the Profile page's own large avatar (`app.profile.tsx`) compute a user's initials with two different algorithms — the nav bar takes the first letter of the **first** and **last** word of the name; the Profile page takes the first letter of the **first two** words. For a 2-word name these agree; for a 3+-word name they diverge (e.g., "M2.1 P0 Verified Name" → "MN" in the nav, "MP" on Profile). This matches an incidental observation flagged-but-unconfirmed in `PR_REPORT_M2.1-P0.md`; this audit traced it to its root cause and confirms it is a real, reproducible, low-severity cosmetic inconsistency — not a screenshot artifact. **Non-blocking** (cosmetic only, no data or trust impact beyond a visually differing avatar), but should be logged as a small future fix (unify on one initials function).

**Verdict: Passes**, with one newly-documented, non-blocking cosmetic finding.

---

## 3. Financial Correctness Review

- No calculation, Monte Carlo parameter, tax figure, or eligibility rule was touched by any of the four M2.1 findings — confirmed by re-reading every changed file's diff scope (Risk Profile: pure UI subtraction; Schemes: passthrough endpoint only; Audit: logging only; Accessibility: `className` only; Performance: fetch-sharing and batching only, explicitly verified not to change any computed value).
- `test_planning_service.py`, `test_family_insurance.py`'s recommendation tests, and `test_family_schemes.py`'s cross-endpoint identical-reason-text test all pass unchanged in the fresh 330-test run.
- The dashboard query optimization's Architecture Review explicitly re-confirmed every card's computation is byte-for-byte identical, just relocated from fetch-then-compute to receive-then-compute — re-verified in this audit by reading `family_dashboard_service.py` directly.

**Verdict: Passes.**

---

## 4. Security Review

- **Insurance audit logging gap (v1 condition) is closed**: `create_policy()` and `replace_policy_coverage()` both now write `AuditLog` rows with `before_state`/`after_state`, matching the existing Family module's audit pattern exactly. Confirmed present in current code.
- **No new attack surface**: the Schemes endpoint is a read-only `GET`, requires the existing `get_current_user` dependency (confirmed present in `family.py`), and returns only the requesting user's own household data — no new IDOR surface introduced (evaluated against the same household-scoping pattern every other Family endpoint uses).
- **No secrets, credentials, or PII handling changed** by any of the five M2.1 changes.
- **Rate limiting, CORS, and auth middleware** (`backend/app/middleware/`) were not touched this sprint — unchanged from v1's passing security posture.

**Verdict: Passes.**

---

## 5. Accessibility Review

- **Keyboard focus indicators**: confirmed present (non-zero `focus-visible:` count) in all 6 previously-flagged files, and live-verified via real Tab-key navigation (not just `className` presence) on two of them.
- **Focus order**: unchanged by construction (every fix was a `className`-only addition; no DOM reordering).
- **Interactive controls reachable by keyboard**: reconfirmed no `<div onClick>` anti-pattern exists anywhere in the Family module.
- **Screen-reader labels**: no new gap found during the Accessibility Polish pass; existing patterns (icon `aria-hidden`, `<label>`-wrapped checkboxes, `role="status"`/`role="alert"`) remain correctly in place.
- **Color never the only signal**: reconfirmed (see Product Health Review above).
- **Open, non-blocking item (unchanged from v1, correctly out of scope for M2.1)**: the shared `field-input` CSS utility (`code/src/styles.css`) still sets `outline: none` with only a border-color change on focus — a weaker treatment than the ring pattern applied elsewhere. This is an app-wide, cross-cutting concern deliberately not touched under "do not redesign layouts" / Family-screens scope.

**Verdict: Passes**, one pre-existing, explicitly out-of-scope, non-blocking item remains (unchanged from v1's framing).

---

## 6. Performance Review

- **Dashboard query count**: measured (not estimated) reduction from 25 to 22 SELECT queries per `GET /family/dashboard` call — re-confirmed present in current code via the module-level comment and the `_safe("members_list", ...)`/`_safe("goals_with_tags", ...)` shared-fetch pattern in `family_dashboard_service.py`.
- **N+1 pattern**: `list_policies_with_coverage()`'s per-policy coverage lookup was batched into one query via `_covered_members_for_policies()` — confirmed present; the fix scales correctly (1 query regardless of policy count, versus the old N).
- **One duplication remains, deliberately deferred**: the cross-service `uncovered_parents()` call between the Parents card and the Recommendations feed. This is correctly documented as non-blocking debt rather than silently dropped — closing it would require coupling two services (`family_dashboard_service` and `family_recommendations_service`) that are deliberately kept independent, a materially larger change than "optimize a verified inefficiency."
- No new N+1, unbounded query, or performance regression was introduced by any M2.1 change — confirmed by re-reading every touched function.

**Verdict: Passes.**

---

## 7. Technical Debt Review

Consolidated list of all known, non-blocking debt as of this re-certification (carried forward from v1 where still open, closed items removed, new items added):

| Item | Status | Severity |
|---|---|---|
| ADR-001 status line stale ("Proposed") despite being enforced in production | Still open (v1 carryover) | Cosmetic / documentation |
| ~113 root-level `.md` research/report files, mostly untracked in git | Still open, slightly worse than v1 (was ~70) — this sprint added ~20 more review documents | Documentation hygiene, non-blocking |
| `field-input` CSS utility's weaker focus treatment (app-wide) | Still open (v1 carryover, correctly out of scope for M2.1) | Accessibility, low severity |
| Cross-service `uncovered_parents` duplication (Parents card vs. Recommendations feed) | Still open (newly documented in M2.1-P4, deliberately deferred) | Performance, non-blocking at current scale |
| Task 3's self-member eligibility gap (a user's own scheme eligibility is never evaluated, only family members') | Still open (v1 carryover, reconfirmed in M2.1-P1's Dependency Validation) | Feature gap, documented and honest in UI |
| 6 of 9 seeded government schemes have no configured eligibility rules | Still open (v1 carryover) | Correct, honest "not yet configured" behavior — not a defect |
| Avatar-initials algorithm mismatch between top-nav and Profile page | **New**, first confirmed in this re-certification | Cosmetic, low severity |
| No delete/deactivate action exists for insurance policies (so no corresponding audit action exists either) | Still open (v1 carryover, reconfirmed in M2.1-P2) | Feature gap, not a defect — nothing to audit-log until the action exists |

None of the above is assessed as blocking for production.

**Verdict: Passes** — debt is tracked, explained, and consistently non-blocking; nothing was silently dropped.

---

## 8. Future Compatibility Review

- All five M2.1 changes are additive or internal-only: no schema migration, no removed field, no changed API contract (only a new endpoint, `GET /family/schemes`, and new optional/internal parameters on private functions).
- The optional `covered_ids` parameter added to `uncovered_parents()` is backward-compatible by construction (defaults to `None`) — does not constrain how Milestone 3+ features could extend this function further.
- The Schemes screen's reuse of existing services (rather than a parallel implementation) means Milestone 3 work on scheme eligibility rules only needs to update one place.
- No decision made this sprint forecloses a future architectural option; the one deliberately-deferred item (cross-service `uncovered_parents` duplication) was left specifically to preserve service independence for future flexibility, not out of neglect.

**Verdict: Passes.**

---

## 9. End-to-End User Journey Review

Live-verified this session with a fresh test account (`m2-recert-2026-07-08@example.com`, created and fully cleaned up after):

1. **Registration → Login**: succeeded via the real running backend and Postgres (not mocked).
2. **Dashboard**: renders correctly for a new, empty account (all-zero state, no errors).
3. **Profile**: shows exactly Full Name / Email / Household — confirmed no Risk Profile field anywhere.
4. **Family Home**: empty state ("It's just you right now") renders correctly with a clear next action; all six dashboard cards and the "Government Schemes" link render correctly, positioned between Insurance and Recommendations as designed.
5. **Government Schemes screen**: loads correctly, shows the honest empty-state bucket behavior ("Not eligible — show 9 more," collapsed) for an account with no family members yet.
6. (From the M2.1-P4 verification earlier this session, same live environment): with a parent (insurance gap) and an SSY-eligible child added, the Dashboard, Insurance, and Recommendations screens all correctly showed the insurance recommendation and the SSY scheme match, consistent across every card that reads them.

No broken navigation, no console errors observed, no visual regression from prior sessions' screenshots of the same screens.

**Verdict: Passes.**

---

## 10. Product Consistency Review

- **Terminology**: "Government Schemes" (nav label) / "Personalized matches for your family, bucketed by eligibility" (description) is consistent with the Recommendations feed's own SSY citation — same scheme, same wording, verified in `test_family_schemes.py`'s byte-identical reason-text test (still passing).
- **Dashboard vs. dedicated screens cannot disagree**: the Parents card and the Insurance recommendation share one authority (`uncovered_parents()`); the Schemes screen and the Recommendations feed share one authority (`evaluate_household_eligibility()`). Both properties re-verified unchanged by this sprint's query optimization (same authoritative sources, only fetched more efficiently).
- **New inconsistency found** (see Product Health Review): the avatar-initials mismatch between the top-nav and the Profile page — a genuine, if minor, product consistency defect, newly confirmed in this audit.

**Verdict: Passes**, with the one newly-found, non-blocking cosmetic item noted above.

---

## Regression Check (explicit)

- Backend: **330/330 tests passing**, 97.53% coverage, `ruff check app/` clean, `mypy --strict app/` clean — all run fresh during this audit, not reused from a prior session's output.
- Frontend: `tsc --noEmit` clean, `eslint` clean across the Family module — run fresh during this audit.
- Live verification: fresh registration → login → navigation across Dashboard, Profile, Family, Schemes succeeded with no errors, on the real running application and database.

**No regressions found.**

---

## Final Decision

# CERTIFIED FOR PRODUCTION

## Remaining Technical Debt (all non-blocking)

1. ADR-001's stale "Proposed" status line (documentation only).
2. Documentation sprawl — ~113 root-level report files, mostly untracked.
3. `field-input` CSS utility's weaker focus treatment (app-wide, not Family-specific).
4. Cross-service `uncovered_parents` duplication between the Parents card and Recommendations feed (2–3 extra queries at current scale; deliberately deferred to preserve service independence).
5. Task 3's self-member eligibility gap (a user's own scheme eligibility is never evaluated) — honest, documented limitation, not a defect.
6. 6 of 9 seeded government schemes have no configured eligibility rules yet — correct "not yet configured" behavior.
7. Avatar-initials algorithm mismatch between the top-nav and Profile page (newly found, cosmetic).
8. No insurance policy delete/deactivate action exists yet (so nothing to audit-log there yet — not a gap, an unbuilt feature).

## Deferred Features (by design, not oversight)

- Government scheme eligibility for the account owner's own facts (only family members are evaluated today).
- Full eligibility-rule configuration for 6 of 9 seeded schemes.
- Insurance policy deletion/deactivation.
- Shared-household access for multiple logins (ADR's `resolve_owned_household` is already written against this future case, per its own docstring, but no UI or second-login support exists yet).

## Recommended Milestone 3 Starting Point

Given the codebase is now clean, fully tested, and free of the four conditions that blocked full certification, Milestone 3 planning should:

1. **Start with the documentation-hygiene item** (debt #2) as a low-risk, zero-code-change first task — consolidating or archiving the ~113 root-level reports before Milestone 3 adds its own. This is the single easiest item to clear and prevents the sprawl from compounding further.
2. **Fix the avatar-initials mismatch (debt #7) and the ADR-001 status line (debt #1)** as trivial, low-risk warm-up fixes before Milestone 3's real feature work begins — both are one-line-scale corrections with no architectural risk.
3. **Treat the two remaining scheme-related gaps (debt #5, #6) as natural Milestone 3 backlog items** if Milestone 3's scope includes deepening the Government Schemes feature — they are already well-documented and scoped, not new research.
4. **Defer the cross-service query duplication (debt #4)** until either (a) household sizes in production data actually approach a scale where it matters, or (b) Milestone 3 happens to touch `family_recommendations_service.py` for an unrelated reason, at which point the coupling cost of fixing it is already being paid.

No architectural blockers exist for beginning Milestone 3 feature work once the above light housekeeping is optionally addressed.
