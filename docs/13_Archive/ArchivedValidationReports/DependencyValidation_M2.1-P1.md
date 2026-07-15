# Dependency Validation — Milestone 2.1-P1 (Government Schemes Screen)

**Date:** 2026-07-07
**Source:** `Milestone2CertificationReport.md` §4/§13/§14 — PCA-7 ("zero government-scheme information visible") partially, not fully, resolved; the Contract's §11 Family Government Schemes screen was never built.

## Checklist

| Requirement | Status |
|---|---|
| Scheme Eligibility Service (Task 3) | ✅ `scheme_eligibility_service.evaluate_household_eligibility(db, household_id, as_of=None) -> dict[EligibilityBucket, list[EligibilityResult]]` — already returns all three buckets (`eligible`/`potentially_eligible`/`not_eligible`) for the whole household in one call. This is exactly the shape a Schemes screen needs; nothing about it needs modification. |
| Recommendation Aggregation Service (Task 11) | ✅ `family_recommendations_service.py` already calls this same function for its "eligible"-only scheme recommendations — confirmed no second implementation of eligibility evaluation exists anywhere. |
| Existing endpoint exposing all three buckets | ❌ **None.** Two existing consumers only ever see a narrow slice: `family.py`'s `_eligible_schemes_for()` checks SSY only (inline Add-Child callout); `family_recommendations_service.py` consumes only the `"eligible"` bucket. A new, thin endpoint is required to expose the full bucket dict — this is new *plumbing*, not new *eligibility logic*. |
| Seeded scheme data (verified against the real dev database, not assumed) | 9 schemes seeded (`PPF`, `EPF`, `NPS`, `SSY`, `SCSS`, `NSC`, `KVP`, `APY`, `PMVVY`); only **2 have seeded eligibility rules** (`SSY`: max_age<10 + gender=female; `SCSS`: min_age>=60). `PMVVY` is `closed_to_new`. The other 6 (`PPF`/`EPF`/`NPS`/`NSC`/`KVP`/`APY`) have zero seeded rules, so `evaluate_household_eligibility()` correctly buckets them "not_eligible" with "criteria not yet configured" for every household, always — an honest, pre-existing state (Rule 4: never invent a policy fact), not something this finding can or should fix. |
| Known, pre-existing limitation (documented in Task 3's own source, not new) | `evaluate_household_eligibility()` only evaluates non-`self` members (spouse/child/parent/other) — a `self` member's own eligibility is never evaluated, since it would need a different join to `UserProfile`. This means the Schemes screen, built on this function unmodified, **will never show anything about the user's own eligibility** — only their family members'. This is Task 3's own documented, deliberate scope boundary, not a defect this finding introduces or is responsible for closing. |
| Frontend route | ❌ None exists (`/app/family/schemes` was never built — confirmed, `code/src/routes/` inventory). |
| Existing UI pattern to reuse | ✅ `FamilyPlanningDesign.md` Part 7 already specifies the exact three-bucket mockup (✅ Eligible / 🟡 Potentially eligible / ⚪ Not eligible, collapsed behind "Show N more"). `Milestone2ImplementationContract.md` §11 specifies the API contract and business rules already, unchanged since originally written. |
| Existing frontend patterns to reuse (not reinvent) | The `<details>/<summary>` collapsed-disclosure pattern (Tasks 10/11), the card-link pattern from Family Home, `AppShell` layout, loading-skeleton/error-state conventions established in every other Family screen this milestone. |

## Conclusion

**No blocker.** Every backend piece this screen needs already exists and is certified (Task 3). The only new backend work is one thin, read-only router endpoint that calls `evaluate_household_eligibility()` directly and returns its full output — no new eligibility logic, no new persistence. Proceeding to Root Cause Analysis.
