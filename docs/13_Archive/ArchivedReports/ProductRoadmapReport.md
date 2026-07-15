# Product Roadmap Report

**Date:** 2026-07-06
**Input:** Directly built from `FeatureGapAnalysisReport.md`'s build-now/later/never verdicts — no feature appears in this roadmap that wasn't independently argued for in that report.

---

## Version 2 — "India-Aware Planning Core"

**Theme:** Close the highest-leverage, verified gaps from Phases 1-6 without taking on new regulatory/security categories (no account aggregation, no AI-advisor overhaul yet).

- Tax Regime Comparison Engine (Feature Gap #1)
- Household schema + aggregate net-worth view (Feature Gap #3)
- Nominee management (Feature Gap #5, time-boxed to the Sept 2026 SEBI deadline)
- Cash-flow forecasting (Feature Gap #6)
- Insurance adequacy calculator (Feature Gap #7)
- Goal prioritization / multi-goal surplus allocation (Feature Gap #9)
- Debt-to-income ratio, retirement corpus derivation, education-planning category inflation, family-floater-vs-standalone recommendation (Feature Gap #11-21, all "build now")
- Government scheme directory (browse/compare, surfacing Phase 1's research directly)

**Why this grouping:** every item here is schema-cheap (Phase 5 already designed it) and regulatory-light relative to V3's items. This is the version that makes Northstar's existing Monte Carlo strength *usable* for India-specific planning, without yet taking on the two hardest problems (account aggregation, explainable AI).

## Version 3 — "Connected & Explained"

**Theme:** The two structurally hardest features, each requiring dedicated groundwork before the feature itself is built.

- **Account Aggregation** — contingent on a dedicated research phase into India's Account Aggregator (AA) regulatory framework and a security architecture review (Feature Gap #2's explicit "build later, research first" verdict)
- **Explainable AI Advisor** (confidence scores, citations, structured reasoning) — contingent on the SEBI Research Analyst/Investment Adviser classification question being resolved (Feature Gap #10)
- HUF eligibility feature (logic + UI, schema already exists from V2-adjacent work) — Feature Gap #4's "build later" item
- NRE/NRO asset modeling, HNI PMS/AIF holdings (Feature Gap #11-21's "build later" items) — contingent on the unverified NRI DTAA/TDS research gap (Phase 4) being closed first for the NRI item specifically
- ULIP/REIT/debt-fund tax-treatment engine (Feature Gap #11-21)

## Version 4 — "Decumulation & Life-Stage Completeness"

**Theme:** Features that are technically ready but were explicitly deferred pending a business-facing question this engagement cannot answer alone.

- **Decumulation/sustainable-withdrawal engine** (Feature Gap #8) — **explicitly gated on confirming Northstar's actual user-base age/life-stage distribution first**; this is placed in V4 not because it's technically hard (it's one of the cheaper builds on the whole list, reusing the existing Monte Carlo engine) but because building it before knowing whether current users are pre- or post-retirement would be prioritizing based on assumption, which is exactly what this engagement was asked to avoid
- Simplified estate/document-status reminder (the deliberately-scaled-down alternative to Kubera's "Dead Man's Switch," Feature Gap #11-21)
- Presumptive-taxation support for freelancers/business owners — contingent on the unverified research gap (Phase 4) being closed

## Enterprise Version (not sequenced by number — a distinct product line, not a later version of the same product)

Not researched in depth this engagement (no enterprise-specific persona or requirement was part of Phases 0-6's scope). Flagged only as a placeholder: an enterprise/B2B version (e.g., white-labeled for employers as an employee financial-wellness benefit) would need its own persona research, its own data-ownership/multi-tenancy model, and likely reuses the household-aggregation schema (Phase 5) as a starting point for a different reason (company-to-employee, not family-to-family) — genuinely out of scope to design further without dedicated research.

## Advisor Version (CFP/RIA-facing)

Also not researched this engagement. Would require: a distinct login/role model (an advisor viewing multiple clients' data, which is a materially different permission model than the household view in Phase 5), and likely a formal SEBI Investment Adviser registration for Northstar itself if it were to support licensed advisors using the platform to deliver advice — a business/legal question, not a technical one, and explicitly flagged as needing its own research phase rather than being sized here.

## Family Version

**This is not a separate version — Version 2 already builds the household/family core as a foundational layer, per Feature Gap #3's "build now" verdict and the cross-persona patterns identified in Phase 4.** Calling this out explicitly because your original brief listed it as a distinct roadmap item, and the honest answer is that treating "family" as a bolt-on later version would contradict this engagement's own finding that household modeling is foundational, not additive.

## AI Version

**Also not a separate version — it's Version 3's explainable-AI-advisor item.** Same reasoning: your brief's structure implies AI as a possible separate track, but this engagement's `AIArchitectureReport.md` explicitly designed the AI layer as a narration layer *on top of* the deterministic Calculation/Policy engines from V2 — it cannot meaningfully exist as an independent version before those engines do.

---

## Roadmap-Level Observation

**The clearest finding from mapping the Feature Gap Analysis onto a roadmap: Version 2 is entirely "build now" verdicts, and every "build later" or "build never [as-implemented]" verdict lands in V3/V4 for a *specific, named reason*** (regulatory research needed, unverified facts, or an unanswered business question about the actual user base) **— not because of arbitrary sequencing.** This is the practical payoff of the challenge-every-assumption framework: the roadmap is a direct, traceable consequence of the gap analysis, not a separately-invented plan.
