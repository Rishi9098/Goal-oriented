# Recommendation Integrity Review — Task 11 (Family Recommendations)

**Date:** 2026-07-07
**Performed before implementation**, per instruction. Extends `RecommendationIntegrityReview_Task10.md`'s guarantees to the aggregation layer — this task adds no new recommendation-generation logic of its own, only a shared envelope and conflict detection over two already-certified sources.

## Every recommendation includes Why / Why Now / Data Used / Missing Information / Confidence

The shared `FamilyRecommendation` schema makes all five fields mandatory (`why: str`, `why_now: str`, `what_information_was_used: list[str]`, `what_information_is_missing: list[str]`, `confidence_score: float`) — there is no code path that constructs one with any field omitted. For the insurance source, all five are read directly from Task 10's already-certified `InsuranceRecommendation`. For the scheme source, `why` is `EligibilityResult.reason` (verbatim, Task 3's own certified text); `why_now` states the age/eligibility-window basis (a genuinely age-gated fact, not invented, since SSY has a max-age ceiling and SCSS a min-age floor — both real eligibility-window facts, not urgency manufactured for effect); `what_information_was_used` lists the member's recorded date of birth (age) and gender where the scheme's rules actually used them; `what_information_is_missing` is empty for anything already bucketed "eligible" (by definition, eligibility couldn't have been confirmed with missing data); `confidence_score` is `1.0` for every scheme recommendation, since eligibility here is a deterministic rule match, not a probabilistic estimate — never a lower, invented number for a case that isn't actually uncertain.

## No recommendation without verified grounding

Scheme recommendations are constructed only from `evaluate_household_eligibility()`'s `"eligible"` bucket — never `"potentially_eligible"` or `"not_eligible"` (those are informational states for a future Schemes screen, not actionable recommendations). No new eligibility rule, threshold, or figure is introduced by this task; every fact quoted was already verified in Task 3/10.

## No recommendation is persisted during read operations

`GET /family/recommendations` computes the aggregation fresh on every call — same reasoning as `RecommendationIntegrityReview_Task10.md` #4: both underlying engines are pure, deterministic functions of current data, and the pre-existing `recommendations`/`recommendation_citations` tables remain untouched (confirmed empty across the whole database at the end of Task 10, and this task adds no write path to them).

## Existing Calculation Lifecycle (ADR-001) remains unchanged

The aggregation service never imports or calls `planning_service.calculate_goal_probability()` or anything in the goals module. Verified by construction (no import) and will be re-confirmed by a permanent test mirroring Task 10's `test_calculation_lifecycle_untouched`.
