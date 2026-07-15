# Dependency Validation — Task 10 (Family Insurance)

**Date:** 2026-07-07
**Performed before any code was written**, per instruction.

## Checklist

| Requirement | Status |
|---|---|
| Tasks 1–9 complete | ✅ `PROJECT_STATE.md` shows explicit "✅ Complete" headings for Tasks 5–9, each followed by the next task's "Stopping here" line, in strict order. |
| `health_policies` / `health_policy_coverage` exist | ✅ Confirmed in `backend/app/models/insurance.py` (migration already applied, per `docs/database.md` line 83) — `policy_type`, `sum_insured`, `annual_premium`, `insurer`, `is_active`; coverage is a join table to `household_members`. Never written to by any existing service — Task 10 is the first consumer. |
| `dependents.has_own_insurance` exists | ✅ Confirmed (`'yes'\|'no'\|'not_sure'`, nullable, migration 007/Task 1). Already captured via Task 6's Add Family Member forms and returned on `FamilyMemberResponse` — no new capture UI needed. |
| No existing insurance router/service | ✅ Confirmed via search — `app/services/family_insurance_service.py` and the new routes on `app/routers/family.py` are this task's own, in-scope deliverable (per `ImplementationChecklist.md` Task 10's own Backend line), not a "blocker" exception. |
| Verified deduction figures exist | ✅ `FamilyHUFPlanningReport.md` line 24: "up to ₹25,000 for a self/spouse/children floater, plus a separate ₹25,000 (₹50,000 if the parents are senior citizens) for a standalone parents' policy." Cross-checked against `GovernmentPolicyReport.md` line 45 (80D: ₹25,000 self/spouse/children; ₹50,000 if 60+) — consistent. The **base** ₹25,000 figure is also present as structured, queryable data: `tax_sections` table, `section_number='80D'`, `limit_amount=25000` (verified live via direct query against this dev DB). The senior-citizen doubling to ₹50,000 is not separately represented as structured data (the schema has one row per section, not per-dependent-category); it is derived as `base_limit × 2`, not a second hardcoded literal. |
| Existing eligibility/age-computation utility | ✅ `scheme_eligibility_service._age_years(dob, as_of)` — exact calendar-date arithmetic (not `days/365.25`), already correctly built and tested in Task 3. Promoted to public (`age_years`) for reuse here, avoiding a second age-computation implementation — the exact kind of duplication this project has already been burned by once (Task 3's own docstring flags the `days/365.25` drift bug this exists to prevent). |
| `Recommendation`/`RecommendationCitation` model | ✅ Exists (`app/models/recommendation.py`), designed for exactly this shape (reasoning, confidence, alternatives, assumptions, citations) but **never written to by any service** — this is the "existing recommendation infrastructure" this task is instructed to reuse. See `RecommendationIntegrityReview_Task10.md` for how (and how not) it's reused. |
| Government schemes vs. insurance separation | ✅ Confirmed distinct: `Scheme`/`SchemeEligibilityRule`/`SchemeRate` (SSY, SCSS, PMVVY — Task 3/11's domain) vs. `HealthPolicy`/`HealthPolicyCoverage`/`TaxSection` (Task 10's domain). No shared table, no shared evaluation function. The only utility crossing the boundary is the pure age-computation helper, which is domain-agnostic arithmetic, not scheme logic. |

## Blockers

None. Proceeding to Recommendation Integrity Review, Data Integrity Review, and User Trust/Design Review.
