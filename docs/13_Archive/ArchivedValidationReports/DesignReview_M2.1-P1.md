# Design Review — Milestone 2.1-P1 (Government Schemes Screen)

**Date:** 2026-07-07

## Backend

One new thin endpoint, no new service logic:

```
GET /api/v1/family/schemes → FamilySchemesResponse {
  eligible: SchemeEligibilityItem[]
  potentially_eligible: SchemeEligibilityItem[]
  not_eligible: SchemeEligibilityItem[]
}
```

`SchemeEligibilityItem { scheme_code, scheme_name, member_name: str | null, reason }` — a direct passthrough of `EligibilityResult`, no reshaping logic. The router resolves the household (`get_or_create_household`, the same pattern every Family endpoint uses) and calls `scheme_eligibility_service.evaluate_household_eligibility(db, household.id)` verbatim — zero new eligibility logic, per Dependency Validation.

## Frontend

New route `/app/family/schemes`, following `FamilyPlanningDesign.md` Part 7's mockup exactly:

- **✅ Eligible** section — always expanded, one card per item, styled like the existing SSY callout / recommendation cards (shield-adjacent icon, cyan accent) so it reads as consistent with what Tasks 6/10/11 already established.
- **🟡 Potentially Eligible** section — always expanded (this is the actionable, forward-looking bucket the Certification Report specifically flagged as having zero visibility today — it must not be buried behind a click).
- **⚪ Not Eligible** section — collapsed by default behind a native `<details>/<summary>` ("Show N more"), matching the same accessible disclosure pattern already used in Tasks 10/11. Per the Root Cause Analysis, this bucket can have multiple rows per scheme (one per member who doesn't qualify) plus one row per unconfigured scheme — collapsing it is not cosmetic, it's the difference between a usable screen and a wall of "no."
- Empty state: "No schemes matched yet" with copy scoped to "your family" (per User Trust Review's self-member-invisibility note), never implying the user's own eligibility was checked.
- Loading: skeleton blocks matching the existing Family screens' pattern.
- Error: the same scoped, reassuring copy pattern every other Family screen uses ("we couldn't load this — your data is safe").
- Card link on Family Home replaces the "Government scheme eligibility" Coming Soon entry (the last remaining Coming Soon item from that list).
- Accessibility: every card uses `aria-hidden` on decorative icons, `focus-visible` rings on the `<details>` summary and the Family Home card link (explicitly checked this time, given the Certification Report's finding that Tasks 10/11 missed this).

## No duplicated logic, verified

The new router function contains a single service call and a schema construction — no filtering, no re-bucketing, no re-deriving a reason string. `family_recommendations_service.py` is untouched by this finding (it continues to independently call the same function for its own "eligible"-only purpose — both are legitimate, parallel consumers of one source, not two implementations).

## What this finding does not do

- Does not touch `evaluate_household_eligibility()` or any Task 3 file — the self-member limitation and the 6 unconfigured schemes are carried forward exactly as they are, documented, not silently worked around.
- Does not modify the Recommendations feed or Dashboard — those remain exactly as certified.
