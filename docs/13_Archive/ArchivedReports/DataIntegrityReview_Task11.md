# Data Integrity Review — Task 11 (Family Recommendations)

**Date:** 2026-07-07
**Performed before implementation**, per instruction.

## Household ownership

`GET /family/recommendations` scopes both underlying calls to the caller's own household (`family_service.get_or_create_household`, the same resolution every Family endpoint uses) — no new authorization pattern introduced.

## A known, documented limitation carried forward, not silently expanded

`scheme_eligibility_service.EligibilityResult` identifies a subject only by `member_name` (a raw string), not a `household_member_id` — Task 3's certified, frozen output shape. This task's conflict-detection groups by that same name string. Two distinct household members sharing an identical name would be a false-negative/false-positive edge case for conflict grouping; this is a real, minor limitation, documented here rather than silently worked around by modifying Task 3's already-shipped, tested service to add a field it was never designed to carry. Given household sizes in this product are small (a handful of named individuals) and name collisions within one household are rare, this is an acceptable, disclosed tradeoff, not a hidden one.

## No duplicate calculations

Confirmed via code review before writing the aggregation: no eligibility rule, age threshold, or deduction figure is recomputed by this task. Every value flows through unchanged from Task 3/10's already-certified functions.

## No stale recommendations

Because nothing is cached or persisted (see `RecommendationIntegrityReview_Task11.md`), the aggregated response is always as current as the two underlying engines already guarantee individually — Task 10's own stale-recommendation guard (excluding an already-covered parent) and Task 3's own current-date evaluation both carry through unchanged.

## Existing Calculation Lifecycle (ADR-001)

No goal, probability, or Monte Carlo table is read or written by this task's code — verified by construction (no import of `planning_service` or `app.models.goal` anywhere in the new aggregation service).
