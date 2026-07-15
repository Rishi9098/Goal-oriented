# Data Integrity Review — Task 10 (Family Insurance)

**Date:** 2026-07-07
**Performed before implementation**, per instruction.

## Household ownership

Every `HealthPolicy` is scoped to `primary_holder_user_id == current_user.id` (existing FK, unchanged). Every `household_member_id` a policy covers is validated against the caller's own household (reusing `family_service.get_or_create_household`, the same resolution every other Family endpoint uses — not a second implementation) before the coverage row is written. A covered member id outside the caller's household returns 422, matching Task 8's established cross-household-tagging pattern rather than inventing a new one.

## Which parents trigger the recommendation — resolved deliberately, not guessed

`Milestone2ImplementationContract.md` §10's Business Rule reads: "If any parent-type household member has `insurance-status = 'no'` or `'not_sure'`..." Its own Acceptance Criteria phrases the negative case as "...or where **all parents are marked 'yes'**, does not [see the recommendation]" — implying, by elimination, that an **unanswered** (`NULL`) status should also count as eligible, not just the two named enum values literally. Resolved in favor of the Acceptance Criteria's framing: the trigger condition is `has_own_insurance != 'yes'` (covers `'no'`, `'not_sure'`, and `NULL`), since an unanswered field carries *less* confidence of coverage than `'not_sure'`, not more. Documented here rather than silently picked either way.

Only **complete** parent-type members (`family_service.is_complete()`) are evaluated — an incomplete placeholder (no name yet) cannot sensibly be the subject of an insurance recommendation.

## Avoiding a stale recommendation

A parent already fully covered by an **active** `HealthPolicy` on file is excluded from triggering the recommendation, even if their `has_own_insurance` answer is stale (`'no'`/`'not_sure'`/unanswered from onboarding, before any policy was recorded). `health_policies`/`health_policy_coverage` are the more current, more authoritative signal once they exist — recommending "get them covered" for someone already recorded as covered would be exactly the kind of stale/contradictory recommendation this engagement has repeatedly flagged and fixed (Task 8's Product Consistency Review, PCA-3's whole premise). This is a deliberate cross-check between two data sources the Contract's own literal Business Rule text doesn't explicitly call for, added because skipping it would produce a demonstrably wrong recommendation.

## Existing calculations remain deterministic

No Monte Carlo, no goal-probability computation, no interaction with `calculate_goal_probability()` anywhere in this task's code. The insurance recommendation is a separate, pure computation with no stored, cached, or path-dependent state — the same inputs always produce the same output, verified by construction (no RNG, no external call, no seed).

## No duplicate calculations

The base ₹25,000 figure is read once from `tax_sections`, not re-derived. The senior-citizen ₹50,000 figure is computed from that one read (`× 2`), not a second independent constant that could drift out of sync if the base figure is ever corrected. Age computation reuses `scheme_eligibility_service.age_years()` (promoted to public) rather than a second date-arithmetic implementation.

## No stale recommendations after data changes

Because the recommendation is computed fresh on every `GET` (see `RecommendationIntegrityReview_Task10.md` §4), it is structurally incapable of going stale relative to the household's current state — editing a parent's `has_own_insurance` answer (Task 6/7's existing edit flow) or adding a policy (this task's own write path) is reflected on the very next load, with no cache to invalidate and no manual refresh required.
