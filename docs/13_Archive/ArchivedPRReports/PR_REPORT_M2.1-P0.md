# PR Report — Milestone 2.1-P0: Risk Profile Persistence Bug

**Date:** 2026-07-07
**Source:** `Milestone2CertificationReport.md` §14, Known Risk #1 (the single highest-priority finding from Milestone 2's certification).

## Summary

Fixed the confirmed, live-reproduced bug where changing "Risk Profile" on `/app/profile` showed a false "✓ Saved" confirmation while silently never persisting. Root cause: this was never a wiring oversight — no account-level risk-profile field has ever existed anywhere in the backend (`User`, `UserProfile`, `FinancialAssumptions` were all checked; only `Goal.risk_profile`, per-goal, is real). Fixed by removing the misleading field entirely, per the user's explicit design decision, rather than building a new backend concept that would constitute new-feature work during a stabilization sprint.

## Review Pipeline

1. **Dependency Validation** (`DependencyValidation_M2.1-P0.md`) — confirmed no backend column/endpoint for this field exists on any of the three plausible models; confirmed the real per-goal equivalent (`app.goals.tsx`) is unaffected.
2. **Root Cause Analysis** (`RootCauseAnalysis_M2.1-P0.md`) — traced the false "Saved" confirmation to `handleSubmit` sending only `full_name`, the initial state hardcoding `riskProfile: "balanced"` with no read path, and classified this as a Product Principle #7 / UX Principle #7 violation, the same failure class PCA-1/PCA-2 already fixed elsewhere in this codebase.
3. **Design Review** (`DesignReview_M2.1-P0.md`) — presented two fix shapes (remove the false capability vs. build a real new account-level field) to the user; **user selected removal** — the smaller, correct-for-a-stabilization-sprint fix, consistent with the PCA-1/PCA-2 precedent.
4. **User Trust Review** (`UserTrustReview_M2.1-P0.md`) — confirmed removing a control that never actually worked is not a capability loss (no prior "save" was ever real), and confirmed nothing else in the product depends on this field's value.
5. **Implementation** — single file, `code/src/routes/app.profile.tsx`: removed the Risk Profile field, its header summary display, the `RISK_OPTIONS` constant, and every `riskProfile` reference from `FormState`, initial state, and the `isDirty` check. Tightened `handleChange`'s type from `HTMLInputElement | HTMLSelectElement` to `HTMLInputElement` now that no `<select>` remains in this file. No backend change (none was ever needed).
6. **Testing** (`Testing_M2.1-P0.md`) — `tsc`/`eslint` clean; grep confirms zero remaining `riskProfile`/`RISK_OPTIONS` references; `git status` confirms exactly one file changed.
7. **Live Verification** — registered a fresh test account, confirmed the field and header label are gone; changed and saved Full Name, confirmed it persisted correctly across a page reload (the form's one genuine save path is unaffected by the fix). Test account fully cleaned up afterward.
8. **Documentation** — this report, `PROJECT_STATE.md` (new Milestone 2.1 section), `CHANGELOG.md`.

## Files Changed

| File | Change |
|---|---|
| `code/src/routes/app.profile.tsx` | Removed the Risk Profile field, header summary, `RISK_OPTIONS`, and all related state/logic. |

## Verifying No Silent Data Loss

No data existed to lose — the field was never backed by a real column, confirmed by reading every field on `User`, `UserProfile`, and `FinancialAssumptions`. Removing it removes a false claim, not a real capability.

## Verifying No Misleading UI Remains

Live-verified: the field, its header label, and any trace of it in source are gone. The remaining form (Full Name, Email, the read-only Household display) makes no claim it can't fulfill.

## Verifying This Doesn't Regress Real Functionality

Live-verified: Full Name changes still save correctly and persist across a reload — the one genuine save path this form has was untouched by the fix.

## Known, Not Fixed Here (Scope Discipline)

An incidental observation during live verification — the top-nav avatar initials appeared to differ from the Profile page's own avatar initials in one screenshot after a name change. Not confirmed as a real bug (may be a screenshot rendering artifact) and **not investigated or fixed as part of this finding**, per "implement exactly one finding at a time." Noted in `PROJECT_STATE.md` for a future look if it recurs.

## Rollback

Revert the one file change. No migration, no backend change to reverse.

---

## Definition-of-Production-Ready Checklist (this finding's contribution)

- [x] P0 issue resolved
- [x] No silent data loss
- [x] No misleading UI (for this field)
- [x] No read operation mutates state (unaffected by this change — was already true)
- [ ] Audit logging complete — unrelated to this finding, tracked separately in `Milestone2CertificationReport.md` §13
- [ ] Accessibility passes — unrelated to this finding, tracked separately
- [ ] Product Consistency passes — this finding closes one Known Risk; others remain open per the Certification Report
- [ ] First-Time User Review passes — not re-run as a full pass for a single-finding fix; the User Trust Review above covers this finding's own trust impact
- [x] Architecture Health passes (for this change — single frontend file, no new pattern, no drift)
- [x] Financial Correctness passes (for this change — no financial calculation touched)
- [ ] Milestone Certification = CERTIFIED FOR PRODUCTION — not yet; this is one of multiple findings required before re-certification

**Stopping here per instruction. Awaiting approval before beginning the next Milestone 2.1 finding.**
