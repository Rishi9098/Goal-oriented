# Recommendation Engine Design Report

**Date:** 2026-07-06
**Scope:** This report covers the engine *mechanics* specifically — how candidate recommendations get generated, ranked, and conflict-resolved for a single user at a single point in time. `PolicyEngineReport.md` covers *what data layers* feed a recommendation; `AIArchitectureReport.md` covers *how it gets narrated to the user*. This is the piece in between: the actual decision logic.

---

## Recommendation Generation Is Trigger-Based, Not Constantly Polling

Recommendations should be generated in response to specific, named triggers — not a background job constantly re-evaluating every possible rule against every user, which would be wasteful and would also risk surfacing a recommendation at a confusing moment (e.g., mid-onboarding, before the user has entered enough data for it to be meaningful).

**Verified trigger list, drawn directly from Phases 1-6:**

| Trigger | Example recommendation generated |
|---|---|
| Household member added with `relationship = daughter` and age < 10 | SSY suggestion (Phase 1/3) |
| Dependent parent recorded | Family-floater-vs-standalone insurance comparison (Phase 3) |
| Scheme rate changes (quarterly data refresh) | Re-evaluate any recommendation that cited the changed rate; notify if the conclusion flips |
| Tax year rolls over (or user's income/deduction data changes materially) | Re-run Tax Regime Comparison (Feature Gap #1) |
| Goal added while other active goals exist and combined ideal contribution exceeds recorded surplus | Goal Prioritization allocation (Feature Gap #9) |
| User age crosses 60 in recorded profile | Surface SCSS, flag any NPS/retirement-related recommendations for withdrawal-phase re-evaluation |
| HUF funding-source fields become populated (ancestral property or business income recorded) | HUF eligibility assessment unlocks (was gated before) |
| New asset recorded with `product_class` requiring nomination (per SEBI rule) and no nominee on file | Nomination reminder |

## Ranking Multiple Candidate Recommendations

When more than one trigger fires (a realistic case — adding a dependent parent could simultaneously suggest an insurance change *and* unlock an HUF-adjacent consideration if a business also exists), the engine needs a deterministic ranking, not an arbitrary order:

1. **Regulatory/deadline-bound items first** (e.g., nomination reminders ahead of the September 2026 SEBI deadline) — these have an external clock Northstar doesn't control.
2. **High-confidence, high-reach items next** (per Feature Gap Analysis's users-benefited scoring) — e.g., a Tax Regime Comparison outranks an HUF suggestion for the same user, consistent with Feature Gap Analysis's explicit verdict that HUF is narrow-reach even when technically eligible.
3. **Company-policy soft-preferences and best-practice-weighted items last** — these are genuinely optional, lower-stakes suggestions (Layer 2/3 from the Policy Engine) that should not crowd out higher-priority items in a user's recommendation feed.

This ranking is itself a `company_policies` row (Phase 5/Policy Engine, `policy_type = 'ranking_weight'`) — **the ranking logic is configurable data, not hardcoded application logic**, consistent with the whole engagement's central design principle.

## Conflict Resolution

Two recommendations can genuinely conflict — e.g., "increase NPS contribution" (tax-efficiency-driven) versus "build emergency fund first" (liquidity-driven) when surplus is limited. The engine does not silently pick one:

1. Both candidate recommendations are computed in full (each with its own confidence/citations).
2. A **hard-precedence rule** applies where one is genuinely a prerequisite for the other's soundness — e.g., "emergency fund below 1 month of expenses" is a hard precedence override against any tax-optimization suggestion, because no tax-efficiency argument justifies illiquidity when a household has essentially no buffer. This precedence relationship is itself an explicit `company_policies` row, not an implicit ordering buried in code.
3. Where no hard precedence applies, **both are shown, with the tradeoff stated explicitly** — per your brief's requirement that every recommendation include "tradeoffs" — rather than the engine silently suppressing one. This is a deliberate design choice: a recommendation engine that hides the existence of a reasonable alternative is less trustworthy than one that shows two options and explains the tradeoff, even if slightly more cognitively demanding for the user.

## What This Engine Explicitly Does Not Do

- It does not attempt automatic execution of any recommendation (no auto-investing, no auto-nominee-filing) — every output is a suggestion for the user to act on elsewhere, consistent with Northstar's current architecture having no brokerage/execution capability at all (Competitor Analysis: Northstar is a planning layer, not a broker, and should stay one).
- It does not silently re-rank or suppress a previously-shown recommendation without a visible reason (e.g., "this recommendation is no longer shown because the PPF rate changed on [date]") — an audit-friendly design, directly enabled by the `AUDIT_LOGS` table (Phase 5).
