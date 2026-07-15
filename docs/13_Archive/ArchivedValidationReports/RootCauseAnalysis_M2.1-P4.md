# Root Cause Analysis — Milestone 2.1-P4 (Dashboard Query Optimization)

**Date:** 2026-07-08

## Why the duplication exists

Task 12's Family Dashboard was deliberately designed with **per-card failure isolation** (`IntegrationIntegrityReview_Task12.md`) — each of the six cards computes under its own `_safe()` guard so one card's failure never takes down the whole dashboard. This is a genuinely good design decision, praised explicitly in `Milestone2CertificationReport.md` §9. The cost of that decision, not previously measured, is that two cards independently fetching the *same* underlying data (household members; goals-with-tags) each ran their own copy of an identical query, because each card's function was written as a fully self-contained unit with no shared-fetch mechanism.

The intra-function duplicate (`_covered_member_ids` called twice inside `compute_insurance_recommendation`) has a different, simpler root cause: `uncovered_parents()` was extracted from `compute_insurance_recommendation()` during Task 12 specifically so the Parents card and the recommendation could share one authority (`DependencyValidation_Task12.md` Finding 2) — but the caller (`compute_insurance_recommendation`) still needed `covered_ids` itself for a separate purpose (the "N existing policy coverage record(s) on file" text in `what_information_was_used`), and re-fetched it rather than reusing what `uncovered_parents()` had already computed internally.

The N+1 in `list_policies_with_coverage()` has the most ordinary root cause: it was written as the simplest possible correct implementation (fetch policies, then fetch each one's coverage) without anticipating a household with many policies — reasonable for Milestone 2's typical household size, but a real inefficiency at scale.

## Is any of this a correctness bug?

**No.** Every duplicate query returns the exact same result as its sibling call (same household, same point in time, same transaction) — this is redundant work, not incorrect work. No test failure, no data inconsistency, no wrong value was ever produced by any of these patterns.

## Scope of the fix

1. Share one fetch of household members between the Dependents and Coverage cards.
2. Share one fetch of goals-with-tags between the Education and Retirement cards.
3. Eliminate `compute_insurance_recommendation()`'s redundant second `_covered_member_ids()` call by computing it once and passing it into `uncovered_parents()` via a new optional parameter (default `None`, preserving every other caller's exact existing behavior).
4. Batch `list_policies_with_coverage()`'s per-policy coverage lookup into one query across all policy IDs.

## What this finding does not do

- Does not touch the cross-service `uncovered_parents` duplication between the Parents card and the Recommendations feed — see `PerformanceReview_M2.1-P4.md` for why this is deferred, not silently ignored.
- Does not change `_safe()`'s failure-isolation architecture, any card's computed values, any API response field, or any calculation/recommendation logic.
