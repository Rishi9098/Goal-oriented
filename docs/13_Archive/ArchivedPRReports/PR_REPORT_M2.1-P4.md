# PR Report — Milestone 2.1 (Dashboard Query Optimization)

**Date:** 2026-07-08
**Source:** `Milestone2CertificationReport.md` §7/§13 — the Family Dashboard issues more queries than necessary; harmless today, worth tightening before household sizes grow.
**Note on numbering:** instructed as "P3," matching the label already used for Accessibility Polish. This report and its companions use the `M2.1-P4` file suffix purely to avoid collision — referred to by name ("Dashboard Query Optimization") throughout. This is the final engineering finding in this Milestone 2.1 Production Stabilization Sprint.

## Summary

Reduced `GET /family/dashboard`'s query count from a measured 25 to 22 SELECT statements (12%), and eliminated an unbounded N+1 pattern in the Insurance screen's policy-listing query, without changing any business logic, calculation, recommendation logic, or API response. One further duplication was identified, deliberately not fixed, and documented as non-blocking debt — closing it would require coupling two services currently kept independent by design.

## Review Pipeline

1. **Dependency Validation** (`DependencyValidation_M2.1-P4.md`) — traced the full call graph from `get_family_dashboard()` through every function it calls, transitively, and **empirically measured** (via a temporary `AsyncSession.execute` instrumentation, not estimation) 25 SELECT queries for one dashboard load against a realistic household. Identified 4 fixable duplications/N+1 and 1 deliberately out-of-scope one.
2. **Root Cause Analysis** (`RootCauseAnalysis_M2.1-P4.md`) — traced each duplication to its origin: the dashboard's deliberate per-card failure-isolation design (a good decision, whose unmeasured cost was two pairs of cards independently re-fetching identical data), a straightforward oversight (the intra-function double-fetch in `compute_insurance_recommendation`), and an unoptimized simplest-implementation choice (the N+1 in `list_policies_with_coverage`). Confirmed none of this was a correctness bug — every duplicate query returns the identical result as its sibling.
3. **Performance Review** (`PerformanceReview_M2.1-P4.md`) — measured before/after precisely, and made the explicit, reasoned case for **not** fixing the one remaining cross-service duplication (`uncovered_parents` between the Parents card and the Recommendations feed): closing it would require changing `family_recommendations_service.get_family_recommendations()`'s public signature to thread a value through three functions across two files — a materially larger, cross-service change than the four fixes made, and a real risk to the deliberate service independence `RecommendationConflictReview_Task11.md` established.
4. **Architecture Review** (`ArchitectureReview_M2.1-P4.md`) — confirmed no business logic, API response shape, or authoritative data source changed; confirmed the dashboard's failure-isolation architecture is preserved exactly (a shared-fetch failure degrades the same set of cards to `None` as before, since these are deterministic reads, not independently-flaky calls — verified directly via the existing partial-failure tests passing unchanged); confirmed no new coupling between services.
5. **Implementation:**
   - `family_dashboard_service.py`: `get_family_dashboard()` fetches the household-members list and goals-with-tags list once each, sharing them between the two cards that need each (Dependents+Coverage; Education+Retirement). The four affected card-builder functions now receive their data as a parameter instead of fetching it themselves — same computation, same result, no I/O.
   - `family_insurance_service.py`: `uncovered_parents()` gained an optional, defaulted `covered_ids` parameter (every existing caller that doesn't pass it gets identical behavior); `compute_insurance_recommendation()` now computes `covered_ids` once and passes it through instead of querying it twice. New `_covered_members_for_policies()` batches `list_policies_with_coverage()`'s per-policy coverage lookup into one query across all policy IDs.
6. **Testing** — 1 new test (`test_multiple_policies_have_correct_distinct_coverage`) confirming the batched lookup keeps each policy's covered members correctly distinct, not mixed up across policies. Full suite: 330 passed (was 329), 97.53% coverage. `ruff`/`mypy --strict` clean.
7. **Measurement (before/after)** — see below.
8. **Live Verification** — registered a fresh test account, added a parent (insurance gap) and an SSY-eligible child, confirmed the dashboard's JSON response and rendered UI were identical in shape and content to every prior verification session for the same household composition. Test account fully cleaned up.
9. **Documentation** — `PROJECT_STATE.md`, `CHANGELOG.md`, this report.

## Files Changed

| File | Change |
|---|---|
| `backend/app/services/family_dashboard_service.py` | Shared member-list and goals-with-tags fetches; card functions now take pre-fetched data as parameters. |
| `backend/app/services/family_insurance_service.py` | Optional `covered_ids` param on `uncovered_parents()`; dedup in `compute_insurance_recommendation()`; new batched `_covered_members_for_policies()`. |
| `backend/tests/test_family_insurance.py` | 1 new test for the batched-coverage correctness. |

## Measured Query Counts (Before / After)

```
GET /family/dashboard, realistic household (1 parent, 1 child, 1 policy, 2 goals):
  Before: 25 SELECT queries
  After:  22 SELECT queries  (−3, −12%)

list_policies_with_coverage, 2-policy household:
  Before: 3 queries (1 policy list + 1-per-policy N+1)
  After:  2 queries (1 policy list + 1 batched coverage lookup)
  — the gap widens with every additional policy; N+1 is now O(1) for this lookup.
```

Both measured empirically via a temporary `AsyncSession.execute` instrumentation (not part of the permanent test suite; removed after use).

## Verifying Optimization Does Not Change Business Logic

Confirmed by re-reading every touched function: no calculation, eligibility rule, or recommendation logic was added, removed, or altered — only *how* and *how many times* underlying data is fetched.

## Verifying Optimization Does Not Change API Responses

`FamilyDashboardResponse` and `FamilyInsuranceResponse` schemas untouched. Confirmed via the existing test suites (all passing, asserting exact field values) and a live request/response comparison during verification.

## Verifying Authoritative Data Sources Are Preserved

Every fact still originates from the exact same certified function it always did (`family_service`, `family_insurance_service`, `scheme_eligibility_service`, `planning_service`) — this finding changes call frequency, never the source of truth.

## Documentation

`PROJECT_STATE.md` (finding entry), `DependencyValidation_M2.1-P4.md`, `RootCauseAnalysis_M2.1-P4.md`, `PerformanceReview_M2.1-P4.md`, `ArchitectureReview_M2.1-P4.md`, `CHANGELOG.md`, this report.

## Known, Not Fixed Here (Scope Discipline)

The cross-service `uncovered_parents` duplication between the Parents card and the Recommendations feed remains — deliberately, per the Architecture/Performance Review's reasoning above. Non-blocking at current household scale.

## Rollback

Revert the two service files and the one new test. No migration, no schema change, no API contract change to reverse.

---

## Definition-of-Production-Ready Checklist (this finding's contribution)

- [x] No silent data loss (read-only optimization)
- [x] No misleading UI (no user-facing copy changed; API responses verified identical)
- [x] No read operation mutates state (unrelated to this finding, unchanged — still true)
- [ ] Audit logging complete — unrelated to this finding (addressed by the approved P2 finding)
- [ ] Accessibility passes — unrelated to this finding (addressed by the approved Accessibility Polish finding)
- [x] Product Consistency passes (for this finding) — same data, same authoritative sources, verified live
- [ ] First-Time User Review passes — not applicable; purely an internal query-count optimization with zero visible or functional change
- [x] Architecture Health passes (for this change) — no new coupling, no redesign, failure-isolation preserved
- [x] Financial Correctness passes (for this change) — no financial calculation touched
- [ ] Milestone Certification = CERTIFIED FOR PRODUCTION — this was the final engineering finding in this sprint; overall re-certification is a separate step, not automatic from this report

**Stopping here per instruction. This was the final engineering finding in this Milestone 2.1 Production Stabilization Sprint. Milestone 3 has not been started and requires separate review/approval before beginning.**
