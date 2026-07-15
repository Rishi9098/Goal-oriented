# Dependency Validation — Milestone 2.1-P4 (Dashboard Query Optimization)

**Date:** 2026-07-08
**Source:** `Milestone2CertificationReport.md` §7/§13 — the Family Dashboard issues more DB queries than necessary; harmless today, worth tightening before household sizes grow.
**Note on numbering:** instructed as "P3," matching the label already used for Accessibility Polish. This document uses the `M2.1-P4` file suffix (the next sequential slot) purely to avoid collision — referred to by name ("Dashboard Query Optimization") throughout.

## Every query executed for `GET /family/dashboard`, identified by direct code trace and confirmed by live measurement

Traced the full call graph from `family_dashboard_service.get_family_dashboard()` through every function it calls, transitively:

| Card / step | Function(s) called | Queries (before) |
|---|---|---|
| Household resolution | `get_or_create_household` → `resolve_owned_household` | 1 |
| Who depends on me | `list_members_with_completeness` | 1 |
| Education costs ahead | `list_goals_with_tags` | 2 |
| Insurance coverage | `list_members_with_completeness` (again) + `list_policies_with_coverage` + `_covered_members_for` (per policy) | 1 + 1 + N |
| Parents | `uncovered_parents` (parent rows + covered-ids) | 2 |
| Retirement readiness | `list_goals_with_tags` (again) | 2 |
| Emergency readiness | `planning_service.get_dashboard` (goals, assets, liabilities, income, expenses) | 5 |
| Recommendations feed — insurance | `compute_insurance_recommendation` → `_base_80d_limit` + `uncovered_parents` (again) + `_covered_member_ids` (again, directly) | 1 + 2 + 1 |
| Recommendations feed — schemes | `evaluate_household_eligibility` (schemes, rules, members) + category lookup + dependent lookup | 5 |

**Measured baseline (empirical, not estimated):** instrumented `AsyncSession.execute` to count every actual query for one `GET /family/dashboard` call against a realistic household (1 parent with an insurance gap, 1 SSY-eligible child, 1 policy on file, a retirement goal, an education goal) — **25 SELECT queries**, confirmed via a temporary, ad-hoc pytest measurement (removed after use, not part of the permanent suite).

## Duplicate queries identified

1. **`list_members_with_completeness`** — called independently by both the Dependents card and the Coverage card. Same household, same query, same result both times.
2. **`list_goals_with_tags`** (2 queries each call) — called independently by both the Education card and the Retirement card.
3. **`uncovered_parents`** (and its internal `_covered_member_ids` call) — called independently by the Parents card and (via `compute_insurance_recommendation`) the Recommendations feed.
4. **`_covered_member_ids`** — called a second time, directly, inside `compute_insurance_recommendation()` itself, immediately after `uncovered_parents()` already triggered the same query internally — a duplicate *within a single function*, not just across cards.

## N+1 patterns

`list_policies_with_coverage()` fetches all policies in one query, then calls `_covered_members_for()` **once per policy** in a list comprehension — a classic N+1. At today's typical scale (0–2 policies per household) this is invisible; it would matter at real scale (a household with many policies).

## Ensuring the fix does not change business logic, API responses, or authoritative data sources

- No calculation, rule, or eligibility logic lives in `family_dashboard_service.py` or the functions being optimized — confirmed by re-reading every touched function; all contain only fetch, count, and select operations.
- Every card's authoritative data source (`family_service`, `family_insurance_service`, `scheme_eligibility_service`, `planning_service`) remains the single place that computes its respective fact — this finding only changes *how many times* that source is asked the same question, never *what* it's asked or *what* it answers.
- `FamilyDashboardResponse`'s schema is untouched.

## Conclusion

**No blocker.** Three of the four duplications (items 1, 2, and the intra-function case in item 4) can be eliminated with small, safe, single-module changes that preserve every card's existing failure-isolation behavior exactly, and without changing `list_policies_with_coverage()`'s return shape. Item 3 (the cross-service `uncovered_parents` duplication between the Parents card and the Recommendations feed) requires threading a parameter across three functions in two separate service files — judged too invasive for "do not redesign services" and deferred, documented in `PerformanceReview_M2.1-P4.md`.

The N+1 pattern in `list_policies_with_coverage()` **was fixed** (re-assessed after this document's initial draft): batching the covered-member lookup across all policy IDs in one query, rather than one query per policy, is a self-contained, single-function change with an unchanged return type and no business-logic impact — safely in scope, unlike item 3.
