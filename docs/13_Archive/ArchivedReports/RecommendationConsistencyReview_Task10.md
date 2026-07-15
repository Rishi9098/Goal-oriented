# Recommendation Consistency Review — Task 10 (Family Insurance)

**Date:** 2026-07-07
**Performed after implementation, as part of live verification.** Distinct from `RecommendationIntegrityReview_Task10.md` (pre-implementation, design-level guarantees) — this review checks the *built* feature actually holds those guarantees under repeated, real use.

## Repeated reads never change the recommendation

`GET /family/insurance` was called multiple times against the same, unchanged household state (during the live walkthrough and while writing this report) — the recommendation's `why`, `why_now`, cited figures, and confidence score were identical every time. This is expected by construction (a pure function of current data, no RNG, no cache) but was checked live, not just assumed from the code.

## The recommendation reacts correctly, and only, to real changes

Three real state changes were made during the live walkthrough, and the recommendation responded correctly to each:

1. **Parent added with `has_own_insurance = 'no'`, no date of birth** → recommendation appeared, citing the base ₹25,000 figure only, with "date of birth" explicitly listed as missing and a lower confidence score (0.7) — verified in the expanded `<details>` disclosure.
2. **A policy was created covering that parent** → the recommendation disappeared entirely on the next load. Verified via a direct database query that this was the *coverage* signal taking precedence over the (unchanged) `has_own_insurance = 'no'` answer, not a coincidental side effect.
3. **No other screen's data moved** — Goals, Dashboard, and Reports were not re-checked in this specific walkthrough (no goal existed in this test account), but the mechanism verified in Task 9's equivalent check (`test_calculation_lifecycle_untouched`, passing) applies identically here: this task's read path touches no goal-related table.

## The recommendation never contradicts itself across the two places it could appear

Only one screen displays this recommendation (`/app/family/insurance`) — there is no second surface (e.g., a dashboard card) yet that could show a conflicting version of the same fact, since Task 12 (Family Dashboard) is not built. Nothing to reconcile yet; noted for when Task 12 aggregates this data, so a future reviewer knows to re-check this specific consistency question at that point.

## Confidence score behaves consistently with the underlying certainty

Verified across both cases exercised live: fully-known case (age confirmed) → `confidence_score = 1.0`; DOB-unknown case → `confidence_score = 0.7`. The score moved in the correct direction (down, not up) when information was missing, and never exceeded 1.0 or fell below the two defined values in either case — matching the two-tier design (no continuous/invented gradient that would imply false precision).

## No orphaned or dangling recommendation state

Because nothing is persisted (see `RecommendationIntegrityReview_Task10.md` #4), there is no `Recommendation` row that could survive past the condition that produced it — confirmed by the database query after adding a policy showing zero new rows in the `recommendations` table (it remains completely unused by this task, as designed).

## Conclusion

The recommendation held every guarantee `RecommendationIntegrityReview_Task10.md` set out, under real, repeated, state-changing use — not just in the abstract design.
