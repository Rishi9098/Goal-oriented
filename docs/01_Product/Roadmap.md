# Product Roadmap

**Status:** Canonical · **Last verified against code:** 2026-07-06, cross-checked 2026-07-13
**Supersedes:** `ImplementationRoadmap.md`, `PrioritizedBacklog.md`, `ProductConsistencyRoadmap.md` (all archived). `AIAssistantResearch/11_Roadmap.md` remains a linked, standalone appendix under `docs/12_Research/` — its AI-specific roadmap is not duplicated here.
**Method:** every item below traces to a build-now/later/never verdict already argued for in the project's own feature-gap analysis — nothing here is a new, undebated addition.

---

## Version 2 — "India-Aware Planning Core"

**Theme:** close the highest-leverage, verified gaps without taking on new regulatory/security categories (no account aggregation, no AI-advisor overhaul yet). Every item here is schema-cheap (already designed) and regulatory-light relative to V3.

- Tax Regime Comparison Engine
- Household schema + aggregate net-worth view — **already substantially built**, see `docs/02_Architecture/RecommendationEngine.md`
- Nominee management (time-boxed to the relevant SEBI deadline)
- Cash-flow forecasting
- Insurance adequacy calculator
- Goal prioritization / multi-goal surplus allocation
- Debt-to-income ratio, retirement corpus derivation, education-planning category inflation, family-floater-vs-standalone recommendation
- Government scheme directory (browse/compare)

## Version 3 — "Connected & Explained"

**Theme:** the two structurally hardest features, each requiring dedicated groundwork before the feature itself is built.

- **Account Aggregation** — contingent on a dedicated research phase into India's AA regulatory framework and a security architecture review (`docs/09_Security/ThreatModel.md` §2).
- **Explainable AI Advisor** (confidence scores, citations, structured reasoning) — contingent on the SEBI classification question being resolved. The technical groundwork is already substantially designed: `docs/07_AI/AIArchitecture.md` §6–9's Tool Calling/RAG/Safety architecture is this exact feature's future implementation plan.
- HUF eligibility feature (logic + UI — schema already exists).
- NRE/NRO asset modeling, HNI PMS/AIF holdings — contingent on the unverified NRI DTAA/TDS research gap being closed first.
- ULIP/REIT/debt-fund tax-treatment engine.

## Version 4 — "Decumulation & Life-Stage Completeness"

**Theme:** features that are technically ready but explicitly deferred pending a business question this documentation cannot answer alone.

- **Decumulation/sustainable-withdrawal engine** — explicitly gated on confirming Northstar's actual user-base age/life-stage distribution first (one of the cheaper builds on this entire roadmap technically, reusing the existing Monte Carlo engine, but building it before knowing whether current users are pre- or post-retirement would be prioritizing on assumption).
- Simplified estate/document-status reminder (a deliberately scaled-down alternative to a full "digital executor" feature).
- Presumptive-taxation support for freelancers/business owners — contingent on the unverified research gap being closed.

## Not Sequenced (distinct product lines, not later versions of the same product)

- **Enterprise Version** (B2B, white-labeled for employers) — not researched; would need its own persona research, data-ownership/multi-tenancy model, and likely reuses the household-aggregation schema for a different reason (company-to-employee, not family-to-family).
- **Advisor Version** (CFP/RIA-facing) — not researched; would require a distinct login/role model (an advisor viewing multiple clients) and likely a formal Investment Adviser registration for Northstar itself — a business/legal question, not a technical one.

## Explicitly Not Separate Roadmap Items

- **"Family Version"** — not a separate version. Household/family modeling is already a foundational layer (V2's core), not a bolt-on later addition — treating it as a distinct future version would contradict the project's own finding that household modeling is foundational.
- **"AI Version"** — not a separate version. It's V3's explainable-AI-advisor item; the AI layer is designed as a narration layer *on top of* the deterministic Calculation/Policy engines, and cannot meaningfully exist as an independent version before those engines do.

---

## Related Documents
`docs/01_Product/Vision.md` · `docs/03_Engineering/ArchitectureDecisionRecords.md` "Future Decisions" table (the engineering-level counterpart to this product-level roadmap) · `docs/07_AI/AIArchitecture.md` §10 (the AI-specific migration roadmap V1–V5) · `docs/09_Security/ThreatModel.md` (the regulatory risks gating V3)


## Related Tests
None — a roadmap has no test surface; see `03_Engineering/ArchitectureDecisionRecords.md` §"Future Decisions" for the engineering-level counterpart to each roadmap item.

---

*Archived originals: `docs/13_Archive/ArchivedReports/ImplementationRoadmap.md`, `PrioritizedBacklog.md`, `ProductConsistencyRoadmap.md`.*
