# Architecture Review — Milestone 2.1-P4 (Dashboard Query Optimization)

**Date:** 2026-07-08

## Business logic unchanged

Verified by re-reading every touched function after the edits: no calculation, eligibility rule, or recommendation logic was added, removed, or altered. `_dependents_card`, `_education_card`, `_coverage_card`, `_retirement_card` now receive already-fetched data as parameters instead of fetching it themselves — the *computation* each performs on that data (counting, filtering by category, selecting nearest date) is byte-for-byte identical to before, just relocated from "fetch-then-compute" to "receive-then-compute."

## API responses unchanged

`FamilyDashboardResponse`'s schema was not touched. Confirmed via the existing 14-test `test_family_dashboard.py` suite (all passing unchanged) and via a live request/response comparison during verification — identical field names, identical value types, identical content for the same input data.

## Authoritative data sources preserved

Every fact still originates from exactly the same certified function it always did: `family_service.list_members_with_completeness`/`list_goals_with_tags`, `family_insurance_service.list_policies_with_coverage`/`uncovered_parents`, `scheme_eligibility_service.evaluate_household_eligibility`, `planning_service.get_dashboard`. This finding changes *how many times* each is called, never *which* function is the source of truth for its fact, and never adds a second, parallel computation of anything.

## Failure-isolation architecture preserved, not weakened

This was the primary architectural risk to manage. The shared fetches (`members`, `goals_with_tags`) are each wrapped in the same `_safe()` guard every card already used — if a shared fetch fails, every card that depends on it degrades to `None`, exactly as it would have if each card's own independent copy of that same query had failed. Because these are deterministic reads within one transaction (not flaky network calls with independent per-attempt failure probability), a query that fails once fails identically on an immediate second attempt — so sharing the fetch changes nothing about the *set of cards* that go null on a given failure, only how many times the (doomed, if failing) query is attempted. Verified directly: all of `test_family_dashboard.py`'s partial-failure tests (`test_partial_failure_degrades_gracefully`, `test_recommendations_unavailable_flag`) pass unchanged.

## No new coupling between services

`family_dashboard_service.py`'s changes are entirely internal to that one file (plus the small, backward-compatible optional-parameter addition to `family_insurance_service.uncovered_parents()`). No new import was added between services; `family_recommendations_service.py` is untouched by this finding.

## Consistency with "do not redesign services"

The public function signatures most external code depends on are unchanged: `get_family_dashboard(db, user, household) -> FamilyDashboardResponse` (the router's call), `list_policies_with_coverage(db, user)` (used by both the dashboard and `GET /family/insurance`), and `uncovered_parents(db, user, household)` (now with one new optional, defaulted parameter — every existing call site that doesn't pass it gets identical behavior to before). The one deliberately-out-of-scope duplication (cross-service `uncovered_parents`) was left alone specifically because closing it would require changing a public service signature (`get_family_recommendations()`) in a way that couples two services currently kept independent by design.
