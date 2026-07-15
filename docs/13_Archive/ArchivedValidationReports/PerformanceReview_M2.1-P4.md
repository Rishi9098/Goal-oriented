# Performance Review — Milestone 2.1-P4 (Dashboard Query Optimization)

**Date:** 2026-07-08

## Measured query count — before and after (empirical, not estimated)

Instrumented `AsyncSession.execute` to count every actual SQL SELECT issued for one `GET /family/dashboard` call, against a realistic household (1 parent with an insurance gap, 1 SSY-eligible child, 1 policy on file, a retirement goal, an education goal):

| | Queries |
|---|---|
| **Before** | **25** |
| **After** | **22** |
| **Reduction** | 3 queries (12%) |

The 3-query reduction corresponds exactly to the three single-file fixes made: sharing the members-list fetch (−1), sharing the goals-with-tags fetch (−2, since that function itself issues 2 queries per call).

Separately, for the N+1 fix (`list_policies_with_coverage`'s per-policy coverage lookup): measured with a 2-policy household — **before**, this would issue 1 query for the policy list + 2 queries (one per policy) for coverage = 3 total; **after** the batched fix, exactly **1** coverage-lookup query fires regardless of how many policies exist. This wasn't reflected in the 25→22 headline number above because the measurement household only had 1 policy (where N+1 and batched cost the same, 1 query); the win compounds specifically as policy count grows — confirmed by direct measurement showing 1 query for 2 policies (would have been 2).

## Duplicate queries — resolved vs. deferred

| Duplicate | Resolved? | How |
|---|---|---|
| `list_members_with_completeness` (Dependents + Coverage cards) | ✅ Resolved | Fetched once in `get_family_dashboard()`, shared by both cards. |
| `list_goals_with_tags` (Education + Retirement cards) | ✅ Resolved | Same pattern. |
| `_covered_member_ids` (twice within `compute_insurance_recommendation`) | ✅ Resolved | Computed once, passed into `uncovered_parents()` via a new optional parameter. |
| `list_policies_with_coverage`'s per-policy N+1 | ✅ Resolved | Batched into one query across all policy IDs. |
| `uncovered_parents` (Parents card vs. Recommendations feed, via `compute_insurance_recommendation`) | ⏸️ Deferred | See below. |

## Why the `uncovered_parents` cross-service duplication is deferred, not fixed

Eliminating this would require `family_dashboard_service.get_family_dashboard()` to compute `uncovered_parents()` once and thread the result through `family_recommendations_service.get_family_recommendations()` → `_insurance_recommendations()` → `family_insurance_service.compute_insurance_recommendation()` — three functions across two service files, changing `get_family_recommendations()`'s public signature (used independently by the standalone `GET /family/recommendations` endpoint, which has no pre-computed value to pass). This is a materially larger, cross-service change than the four fixes made — closer to "redesigning services" than "optimizing a verified inefficiency," and risks subtly coupling two services that were deliberately kept independent (`RecommendationConflictReview_Task11.md`: "neither function is modified to know about the other"). Left as documented, non-blocking debt, exactly as `Milestone2CertificationReport.md` §7 already characterized it ("harmless today, worth tightening before larger households").

## Performance at realistic scale

At today's typical household size (1–5 members, 1–3 goals, 0–2 policies), the remaining 22-query cost and the deferred duplication are both invisible in practice. The fixes made specifically target the patterns that would compound as household size grows (more policies → the N+1 was genuinely unbounded; more cards reading the same base data → the duplication was a fixed 3-query cost regardless of scale, now removed).

## No new performance risk introduced

Every fix either reduces a query or leaves query count unchanged; none introduces a new query, a new N+1, or an unbounded operation. The batched `_covered_members_for_policies()` uses a single `IN (...)` clause — safe at the scale this application handles (a household's policy count is small, never approaching the thousands where an `IN` clause itself becomes a concern).
