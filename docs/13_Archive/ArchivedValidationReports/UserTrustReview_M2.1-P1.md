# User Trust Review — Milestone 2.1-P1 (Government Schemes Screen)

**Date:** 2026-07-07

## Does every displayed scheme link back to verified policy data?

Yes, structurally guaranteed: every `EligibilityResult` the screen renders comes from `evaluate_household_eligibility()`, which reads live from the seeded `schemes`/`scheme_eligibility_rules` tables — never a hardcoded list. A scheme with no seeded rules is honestly bucketed "not eligible: criteria not yet configured," never silently omitted or guessed into "eligible."

## Is missing eligibility information explained honestly?

Yes, in two distinct ways, both already built into the reused service (not invented for this screen):
1. **Missing member data** (no date of birth) — `_evaluate_rules_for_member` returns `None` for that member/scheme pair rather than guessing a bucket; the member simply doesn't appear for that scheme rather than appearing with a fabricated verdict.
2. **Missing scheme configuration** — a scheme with zero seeded rules reads "Eligibility criteria for {name} are not yet configured," a plain, honest statement rather than a fabricated "not eligible" verdict dressed up as policy fact.

Both are pre-existing, verified Task 3 behaviors — this finding surfaces them, not invents them.

## Can this screen and the Dashboard/Recommendations feed disagree?

**No, structurally.** Both the new Schemes screen and the existing Recommendations feed call the exact same `evaluate_household_eligibility()` function against the same live data, with no caching layer between them. The Schemes screen shows all three buckets; the Recommendations feed shows only the `"eligible"` bucket, reformatted into the recommendation envelope — a subset relationship, not two independent computations that could drift. Live-verified as part of this finding's Live Verification step.

## Trust risk: does showing "Not Eligible" reasons risk feeling judgmental?

The reasons are factual and forward-looking where the rule allows it ("does not yet meet the age 60+ requirement" implies future eligibility, not a permanent no), matching `UX_PRINCIPLES.md` #4/#6. The "Not Eligible" bucket is collapsed by default (per the Contract's own design), so a first-time user isn't confronted with a wall of "no" — only the two buckets that are actually actionable (Eligible, Potentially Eligible) are visible without an extra click.

## Trust risk: self-member invisibility

Per `RootCauseAnalysis_M2.1-P1.md`, the user's own eligibility is never evaluated (a pre-existing Task 3 boundary). This screen must not imply completeness it doesn't have — the empty/no-schemes state and any framing copy must speak about "your family" rather than "you," so a user doesn't wrongly conclude the product checked their own eligibility and found nothing.
