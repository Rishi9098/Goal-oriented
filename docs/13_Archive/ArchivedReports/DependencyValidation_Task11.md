# Dependency Validation — Task 11 ("Family Recommendations")

**Date:** 2026-07-07
**Performed before any code was written**, per instruction. This validation surfaced a genuine task-identity/scope mismatch that must be resolved before Steps 2+ can proceed meaningfully — flagged here rather than guessed at.

## The mismatch

Per the source-of-truth documents this engagement has followed all session (`Milestone2ImplementationContract.md`, `ImplementationChecklist.md`, `PROJECT_STATE.md`), **Task 11 is titled "Family Government Schemes" (`/app/family/schemes`)** — a single-source screen that personalizes the scheme catalog (SSY/SCSS/PMVVY) into Eligible/Potentially Eligible/Not Eligible buckets. Per the Checklist: "Complexity: Low... mostly a presentation layer over Task 3's already-tested service." It has no concept of aggregating multiple recommendation sources, no conflict detection between recommendations, and no dependency on Task 10 (Insurance) at all.

This turn's brief is titled **"Task 11 (Family Recommendations)"** and its actual content — reuse "existing insurance engine" *and* "existing eligibility engine," verify "recommendation engines remain independent," "recommendation aggregation does not duplicate logic," "conflicting recommendations are identified and resolved," run a "Recommendation Conflict Review" — describes an **aggregation-and-conflict-resolution layer over multiple recommendation sources** (Insurance from Task 10 + a scheme-based recommendation). This matches, almost verbatim, what the Contract actually assigns to **Task 12 (Family Dashboard)**'s "Recommendations feed": *"this milestone's two recommendation sources — Insurance and Schemes — already have enough concrete, cited data to populate this format honestly."*

Neither reading is a small difference:

- **If this is literally the Contract's Task 11 (Schemes screen):** most of this turn's specific verification requirements (recommendation conflict review, insurance-engine reuse, "recommendation engines remain independent") wouldn't apply at all — there is only one source (scheme eligibility), nothing to conflict with, and no aggregation to speak of. Implementing the Schemes screen alone would leave several of this turn's explicit review requirements unaddressed by construction, not because they were skipped, but because they don't describe that screen.
- **If this is an aggregation layer combining Insurance (Task 10) + a scheme-based recommendation:** it is buildable *now*, ahead of the full Task 12 Dashboard, by reusing `family_insurance_service.compute_insurance_recommendation()` (Task 10, done) and `scheme_eligibility_service.evaluate_household_eligibility()` (Task 3, done, already exposed to the Add-Child/member-detail SSY callouts but never exposed as a full household-wide recommendation source). This does **not** require the Contract's Task 11 Schemes *screen* to exist first — it can call the eligibility-evaluation function directly, the same way this turn's own reuse list names "existing eligibility engine" rather than "existing Schemes screen."

## Checklist

| Requirement | Status |
|---|---|
| Tasks 1–10 complete | ✅ Confirmed via `PROJECT_STATE.md`'s "✅ Complete" headings in order. |
| Contract's Task 11 (Schemes screen/endpoint) | ❌ **Not built.** No `/app/family/schemes` route, no `GET /family/schemes` endpoint. `PROJECT_STATE.md` itself still reads "Task 11 has not been started" as of the end of Task 10. |
| Existing insurance engine (Task 10) | ✅ `family_insurance_service.compute_insurance_recommendation()` exists, certified, tested (21 tests). |
| Existing eligibility engine (Task 3) | ✅ `scheme_eligibility_service.evaluate_household_eligibility()` exists, certified, tested — currently consumed only by the Add-Child inline callout and (implicitly) member-detail's `eligible_schemes`, never as a full household-wide recommendation source in its own right. |
| Existing household model | ✅ Unchanged, reused throughout the milestone. |

## Blocker

**Not a missing-dependency blocker** (the two engines this turn's brief actually asks to reuse both exist and are certified) — but a **genuine task-identity ambiguity** that determines the entire shape of the work: build the Contract's actual, low-complexity Task 11 (a single-source Schemes screen, most of this turn's review requirements inapplicable), or build the aggregation-and-conflict layer this turn's brief actually describes (matching the Contract's Task 12 concept, buildable now without waiting for a dedicated Schemes screen)?

Per this turn's own instruction — "If blocked: STOP. Generate reports" — stopping here rather than silently picking an interpretation, exactly as `CalculationContextReview.md` did for Task 9's premise-vs-Contract tension.

## Decision (recorded 2026-07-07)

**User confirmed: build the aggregation layer.** Combine Task 10's insurance recommendation with a new scheme-based recommendation (reusing Task 3's `evaluate_household_eligibility()` directly, no dependency on a dedicated Schemes screen), with real conflict-detection logic between sources. No blocker — proceeding to Steps 2–6.
