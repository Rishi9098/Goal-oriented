# Prioritized Backlog & Implementation Milestones

**Date:** 2026-07-06
**Scope:** Version 2 only (`ProductRoadmapReport.md`) — the "build now" set. V3/V4 items are intentionally not broken into milestones yet, since each is explicitly gated on a research or business-decision prerequisite this engagement flagged but did not resolve.

---

## Milestone 1: Household Schema Foundation

**Features:** None user-visible yet — this is the schema groundwork every V2 feature depends on.
**Database:** `households`, `household_members`, `dependents` (Phase 5 Group A). Additive migration only — no existing table touched.
**Backend:** New router/service for household CRUD; `get_dashboard`/`planning_service` extended to optionally aggregate across a household (opt-in, not replacing the existing single-user path).
**Frontend:** No new UI required this milestone (backend/schema only) — deferred to Milestone 2.
**AI work:** None.
**Testing:** New unit tests for household aggregation logic; must not regress the existing 164-test backend suite (per this codebase's own established quality bar, `ImplementationReport.md`).
**Migration:** New Alembic migration, additive only.
**Documentation:** `docs/architecture.md` and `docs/database.md` updated (per this codebase's own documentation-drift lesson from the prior session).
**Complexity:** Medium.
**Dependencies:** None — first milestone.
**Risk:** Low (additive schema, no existing behavior changed).

## Milestone 2: Government Policy Engine Data Layer

**Features:** Government scheme directory (browse/compare) — the first user-visible V2 feature.
**Database:** `schemes`, `scheme_rates`, `scheme_eligibility_rules`, `tax_acts`, `tax_sections`, `tax_regimes`, `tax_slabs`, `policy_citations` (Phase 5 Group B).
**Backend:** New router exposing scheme data; a data-seeding/ingestion process to populate verified Phase 1 figures as the initial dataset (with `source_citation` populated from this engagement's own research, treated as the first "verified" data load).
**Frontend:** Scheme directory browse/compare UI.
**AI work:** None yet — this milestone is data infrastructure, consumed by AI only from Milestone 5 onward.
**Testing:** Data-integrity tests (every rate has a citation, every effective-dated row's ranges don't overlap incorrectly).
**Migration:** Additive.
**Documentation:** New `docs/policy-engine.md` documenting the data model and how to add a new scheme/rate update (this becomes an operational runbook, not just a design doc, since rates change quarterly per Phase 1).
**Complexity:** Medium-high (mostly in getting the initial data-seeding right and correctly modeling PMVVY's `closed_to_new` status per the Phase 1 lesson).
**Dependencies:** None (independent of Milestone 1).
**Risk:** **Medium** — an incorrectly-seeded rate or an incorrectly-modeled eligibility rule ships confidently-wrong financial information; this milestone needs the highest data-review rigor of the whole roadmap, proportionate to Phase 1's own finding that this exact category of error (stale/wrong scheme data) is a real, demonstrated risk class.

## Milestone 3: Tax Regime Comparison Engine

**Features:** The single highest-priority feature identified across the entire engagement (Feature Gap #1).
**Database:** No new tables — consumes Milestone 2's `tax_slabs`/`tax_sections`.
**Backend:** New calculation service implementing Calculation Engine Report #14; new router endpoint.
**Frontend:** Regime-comparison view showing both regimes' computed tax side by side, with assumptions listed explicitly (per `RecommendationEngineReport.md`'s "assumptions used" requirement).
**AI work:** None yet (deterministic calculation only — AI narration comes in Milestone 6+, per `AIArchitectureReport.md`'s explicit sequencing).
**Testing:** Extensive — this calculation touches real financial outcomes directly; needs unit tests covering both regimes, the HUF-exclusion-from-87A-equivalent-rebate edge case (Phase 3), and boundary conditions at each slab threshold.
**Migration:** None beyond Milestone 2's.
**Documentation:** Calculation methodology documented user-facing (not just internally) — given this is the highest-stakes calculation in the roadmap, users should be able to see exactly what was assumed.
**Complexity:** High.
**Dependencies:** Milestone 2 (tax data must exist and be correct first).
**Risk:** **Medium-high** — same rationale as Milestone 2's risk note, compounded by this being a calculation (more logic surface area for bugs) rather than just data.

## Milestone 4: Household-Aware Financial Views

**Features:** Household net-worth aggregate view (Feature Gap #3), cash-flow forecasting (Feature Gap #6).
**Database:** No new tables beyond Milestone 1.
**Backend:** Extends `planning_service` with forward cash-flow projection logic (requires adding recurrence/frequency metadata to `income_sources`/`expenses` — the one schema change in this milestone beyond Milestone 1's).
**Frontend:** Household dashboard view; forward cash-flow chart.
**AI work:** None.
**Testing:** Household-permission tests (does member A's data leak into member B's individual view inappropriately) — flagged as needing explicit test coverage given `FeatureGapAnalysisReport.md`'s note that the permission model is a real, non-trivial design surface, not an afterthought.
**Migration:** Additive column on `income_sources`/`expenses` for recurrence metadata.
**Documentation:** Update `docs/frontend.md`.
**Complexity:** Medium-high (the permission model is the hard part, not the aggregation math).
**Dependencies:** Milestone 1.
**Risk:** **Medium** — privacy/permission risk specifically (per Feature Gap #3's security note), not a financial-correctness risk this time.

## Milestone 5: Goal Prioritization & Remaining Calculation Gaps

**Features:** Goal prioritization (Feature Gap #9), debt-to-income ratio, retirement corpus derivation, education-planning category inflation, insurance adequacy, family-floater-vs-standalone recommendation (Feature Gap #11-21's "build now" batch).
**Database:** `health_policies`/`health_policy_coverage` (Phase 5 Group D) for the insurance items; no new tables for the calculation-only items.
**Backend:** Extends `optimizer.py` for multi-goal allocation (Calculation Engine #18); new insurance-adequacy service.
**Frontend:** Multi-goal allocation view; insurance-adequacy result view.
**AI work:** None yet.
**Testing:** Goal-prioritization algorithm needs both unit tests and the concurrency-style test pattern this codebase already established for `refresh_goal_probabilities` (`ValidationReport.md`, prior session) — multiple goals being optimized should not have ordering-dependent bugs.
**Migration:** Additive (`health_policies` tables).
**Documentation:** Update `docs/backend.md`.
**Complexity:** Medium-high (the allocation algorithm is genuinely the most algorithmically complex item in this milestone).
**Dependencies:** Milestone 1 (household, for insurance coverage), existing `optimizer.py` (already built).
**Risk:** Low-medium.

## Milestone 6: Nomination Reminders

**Features:** Nominee management (Feature Gap #5).
**Database:** `nominees` (Phase 5 Group C).
**Backend:** New router; a scheduled reminder check against the September 2026 SEBI deadline.
**Frontend:** Nominee entry UI on each asset.
**AI work:** None.
**Testing:** Standard CRUD tests, plus a specific test for the "opted_out" declaration path (SEBI's rule explicitly allows a formal opt-out, not just a filled nominee).
**Migration:** Additive.
**Documentation:** Update user-facing help content explaining the actual SEBI rule (with citation, per this whole engagement's sourcing standard).
**Complexity:** Low.
**Dependencies:** None beyond existing `assets` table.
**Risk:** Low — but **time-sensitive**: this is the one milestone with a real external deadline (September 2026), and should not slip behind the higher-complexity milestones above it if the actual deadline is approaching by the time implementation begins.

---

## Cross-Milestone Regression Discipline

Every milestone must re-run this codebase's existing quality gate before merge — `ruff check`, `mypy --strict`, the full `pytest` suite, frontend `tsc`/`vite build`/`eslint` — exactly the gate re-established and verified clean in the prior session's `ImplementationReport.md`. No milestone in this backlog should be the one that lets that gate silently regress.
