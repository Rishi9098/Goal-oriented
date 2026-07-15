# PR Report — Milestone 2.1-P1: Government Schemes Screen

**Date:** 2026-07-07
**Source:** `Milestone2CertificationReport.md` §4/§13/§14 — PCA-7 partially resolved, the Contract's §11 Schemes screen never built.

## Summary

Built the missing Government Schemes screen (`/app/family/schemes`), closing the gap this milestone's Certification flagged: the "Potentially Eligible" bucket — a full third of the three-state eligibility design — had zero UI surface anywhere in the product. This is a direct passthrough of the already-certified Scheme Eligibility Service (Task 3); no new eligibility logic was written anywhere.

## Review Pipeline

1. **Dependency Validation** (`DependencyValidation_M2.1-P1.md`) — confirmed `evaluate_household_eligibility()` already returns all three buckets for the whole household in one call; confirmed the Recommendation Aggregation Service (Task 11) already consumes this same function for its "eligible"-only slice, so no second implementation exists to accidentally create. Verified against the real dev database: 9 schemes seeded, only 2 (SSY, SCSS) have configured eligibility rules.
2. **Root Cause Analysis** (`RootCauseAnalysis_M2.1-P1.md`) — traced the gap to a scoped, previously-surfaced product decision (Task 11 was redirected to the aggregation layer instead of the Contract's dedicated Schemes screen), not a code defect. Explicitly scoped out fixing Task 3's own pre-existing self-member-evaluation limitation or the 6 unconfigured schemes — both carried forward honestly.
3. **User Trust Review** (`UserTrustReview_M2.1-P1.md`) — confirmed every displayed scheme traces to live seeded data, missing information is explained honestly (never guessed into a verdict), and the new screen structurally cannot disagree with the Recommendations feed/Dashboard (same function, no caching).
4. **Design Review** (`DesignReview_M2.1-P1.md`) — one thin backend endpoint (passthrough only); frontend follows the Contract's §11 spec and `FamilyPlanningDesign.md` Part 7's mockup exactly (Eligible + Potentially Eligible expanded, Not Eligible collapsed).
5. **Implementation** — `backend/app/schemas/family_schemes.py` (new), `backend/app/routers/family.py` (new `GET /family/schemes`), `code/src/routes/app.family.schemes.tsx` (new screen), `code/src/routes/app.family.index.tsx` (Coming Soon → real link), `code/src/lib/api.ts` (new types + function).
6. **Testing** — 8 new backend tests, including one asserting reason-text identity between this endpoint and `GET /family/recommendations` for the overlapping "eligible" case (the "cannot disagree" guarantee, tested, not just claimed). Full suite: 325 passed (was 317), 97.52% coverage. `tsc`/`eslint` clean.
7. **Live Verification** — household with an SSY-eligible daughter, a gender-ineligible son, and a mother 3 years from SCSS eligibility. All three buckets rendered correctly; confirmed byte-identical reason text between this screen and the Recommendations feed; confirmed the `recommendations` table stayed at zero rows; test account cleaned up.
8. **Documentation** — `PROJECT_STATE.md`, `CHANGELOG.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum), this report.

## Files Changed

| File | Change |
|---|---|
| `backend/app/schemas/family_schemes.py` | New — `SchemeEligibilityItem`, `FamilySchemesResponse`. |
| `backend/app/routers/family.py` | New `GET /schemes` endpoint. |
| `backend/tests/test_family_schemes.py` | 8 new tests. |
| `code/src/routes/app.family.schemes.tsx` | New screen. |
| `code/src/routes/app.family.index.tsx` | "Government scheme eligibility" Coming Soon → real link. |
| `code/src/lib/api.ts` | New types + `getFamilySchemes()`. |

## Verifying Reuse of the Scheme Eligibility Service

The new router function is a single call to `evaluate_household_eligibility()` plus schema construction — no filtering, no re-bucketing, no re-deriving a reason string. Confirmed by code review.

## Verifying Reuse of the Recommendation Aggregation Service (No Duplication)

`family_recommendations_service.py` is untouched by this finding — it continues to independently call the same eligibility function for its own narrower purpose. Verified via a permanent test that both endpoints produce byte-identical reason text for the same scheme/member.

## Verifying Every Displayed Scheme Links to Verified Policy Data

Every `SchemeEligibilityItem` traces to the seeded `schemes`/`scheme_eligibility_rules` tables via `evaluate_household_eligibility()` — no hardcoded scheme list, no fabricated reason text.

## Verifying Missing Eligibility Information Is Explained Honestly

Live-verified: 6 schemes with no seeded rules read "criteria not yet configured," never a fabricated "not eligible" verdict. A member with no date of birth is simply absent from a scheme's evaluation rather than guessed into a bucket (pre-existing Task 3 behavior, reused unchanged).

## Verifying No Recommendations Are Persisted During Read Operations

`GET /family/schemes` performs zero writes. Live-verified via direct database query: the `recommendations` table remained at zero rows after the walkthrough. Backed by a permanent test.

## Verifying the Dashboard and Schemes Screen Cannot Disagree

Both read the same live `evaluate_household_eligibility()` call with no caching layer between them — structurally incapable of disagreeing. Verified both by a permanent test and live (byte-identical reason text observed on both surfaces for the same scheme/member).

## Documentation

`PROJECT_STATE.md` (P1 entry), `DependencyValidation_M2.1-P1.md`, `RootCauseAnalysis_M2.1-P1.md`, `UserTrustReview_M2.1-P1.md`, `DesignReview_M2.1-P1.md`, `CHANGELOG.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).

## Known, Not Fixed Here (Scope Discipline)

- Task 3's self-member eligibility gap (a user's own eligibility is never evaluated, only family members') — pre-existing, documented, not touched.
- 6 of 9 seeded schemes have no configured eligibility rules and will continue to show "not yet configured" until real rules are seeded — correct, honest behavior, not a defect of this finding.

## Rollback

Revert the new endpoint/schema/route files and the one Family Home link change. No migration, no persisted-state change to reverse.

---

## Definition-of-Production-Ready Checklist (this finding's contribution)

- [x] No silent data loss (read-only feature, nothing persisted)
- [x] No misleading UI (unconfigured schemes and missing member data are stated honestly)
- [x] No read operation mutates state (verified live + permanent test)
- [ ] Audit logging complete — unrelated to this finding (no writes exist to audit)
- [x] Accessibility passes (for this screen) — `focus-visible` on every interactive element, native `<details>` disclosure, `aria-hidden` on decorative icons, `role="alert"` on errors
- [x] Product Consistency passes (for this finding) — verified live and by test that this screen cannot disagree with the Recommendations feed/Dashboard
- [x] First-Time User Review passes (for this finding) — addendum added
- [x] Architecture Health passes (for this change) — zero new eligibility logic, one thin endpoint
- [x] Financial Correctness passes (for this change) — no financial calculation touched, pure eligibility passthrough
- [ ] Milestone Certification = CERTIFIED FOR PRODUCTION — not yet; more findings remain per `Milestone2CertificationReport.md`

**Stopping here per instruction. Awaiting approval before beginning the next Milestone 2.1 finding.**
