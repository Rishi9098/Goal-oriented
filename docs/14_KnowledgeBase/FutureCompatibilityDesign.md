# Future Compatibility Design

**Date:** 2026-07-14
**Purpose:** this V1→V2 restructuring was itself an expensive, all-hands exercise (254 → 31 canonical documents, then a full taxonomy reorganization). This document exists so a V3 documentation pass is never necessary — future growth should extend the existing structure, not replace it. It also states which parts of the *product's own architecture* were already designed with extensibility in mind, so future features build on that intent rather than working around it.

This is a documentation-structure and architecture-extensibility design, not a new roadmap — `01_Product/Roadmap.md` and `03_Engineering/ArchitectureDecisionRecords.md`'s "Future Decisions" table already own the *what's coming*. This document owns *where it goes when it arrives*.

---

## 1. Why the 14-Section Taxonomy Should Not Need to Change Again

The move from V1's 9 sections to V2's 14 sections happened because three topics (AI, Frontend, Database) outgrew being subsections of a shared `02-architecture` folder, and two new synthesis needs emerged (a dedicated Research section, a dedicated KnowledgeBase section for meta-documentation). Both of those were *promotions of existing content to their own top-level section*, not new categories invented from nothing. That's the pattern to repeat: **a new top-level section is justified when a topic has enough independent canonical documents to need its own home — not when a single new document appears.**

Concretely: `12_Research` and `14_KnowledgeBase` already prove the taxonomy can absorb a genuinely new category without touching the other 12. Adding a `15_Mobile` or `16_Plugins` section later, if and when that content justifies it, follows the identical, already-proven mechanical pattern (see §4).

## 2. Where Future Product Lines Land (No New Section Needed Yet)

| Future item (per `01_Product/Roadmap.md`) | Lands in | Why no new section is needed |
|---|---|---|
| Tax Regime Comparison Engine, cash-flow forecasting, insurance calculator (V2 roadmap) | `02_Architecture/CalculationEngine.md` (extend), `04_API/RESTAPI.md` (new endpoints) | Same engine family as the existing Monte Carlo/calculation core — these are new modules inside an existing canonical document, not a new topic. |
| Account Aggregation, Explainable AI Advisor (V3 roadmap) | `09_Security/ThreatModel.md` (already tracks the regulatory gate) → `07_AI/AIArchitecture.md` §6–9 (already designed the Tool Calling/RAG scaffolding this feature will use) | The AI architecture document already anticipated this — see §3 below. No restructuring; just fill in the sections already reserved for it. |
| Decumulation engine, estate reminders (V4 roadmap) | `02_Architecture/CalculationEngine.md`, `02_Architecture/LifeEventEngine.md` | Reuses the existing Monte Carlo engine per the roadmap's own note — extends existing docs. |
| **Enterprise Version** (B2B, not yet researched) | New file `02_Architecture/EnterpriseArchitecture.md` once researched, cross-linked from `02_Architecture/SystemArchitecture.md`; only becomes its own top-level section if it eventually needs 4+ canonical documents the way Frontend/AI/Database did | Likely reuses the household-aggregation schema (`RecommendationEngine.md`) for company-to-employee modeling — extend, don't fork, until proven otherwise. |
| **Advisor Version** (CFP/RIA-facing, not yet researched) | New file in `02_Architecture/` once researched; requires its own auth/role model documented as an extension of `09_Security/SecurityArchitecture.md`, not a replacement | Distinct login/role model is additive to the existing auth middleware design, not a rewrite of it. |
| Future mobile app | New `06_Frontend/MobileArchitecture.md` (or its own `15_Mobile` section only if it grows past 3-4 documents) | The REST API layer (`04_API/`) is already the seam a mobile client would consume — no backend redesign implied. |
| Future public SDK / plugin system | New `04_API/SDKReference.md` and `04_API/PluginArchitecture.md` | `04_API/` already exists as the natural home; a versioned public SDK is an additive reference document, not a new category. |

## 3. Architecture Extension Points Already Designed for This

These are not aspirations — each is a concrete design decision already made in the current canonical documentation, specifically so a future feature would not require re-architecting:

- **`07_AI/AIArchitecture.md` §6–9** (Tool Calling, RAG, Safety, regulatory positioning) — the Explainable AI Advisor (V3) is described in the roadmap itself as reusing this exact scaffolding. This is the clearest example of a document written in V1 already anticipating a V3 feature.
- **`02_Architecture/RecommendationEngine.md`'s household/family schema** — already general enough that the roadmap notes it as the likely reuse point for a future Enterprise (company-to-employee) model, without redesign.
- **`04_API/APIReference.md`'s endpoint structure** — versioned per-domain routers (per `backend/app/routers/`), meaning a future public SDK or mobile client adds new versioned routes alongside existing ones rather than modifying them.
- **`03_Engineering/ArchitectureDecisionRecords.md`'s "Future Decisions" table** — already the designated place for a not-yet-made architectural call to be recorded before it's built, so the eventual real ADR has a documented starting point instead of a blank page.
- **`09_Security/ThreatModel.md`'s explicit regulatory gates** — Account Aggregation and the Advisor Version are both already flagged as blocked on a specific, named research/legal question rather than a vague "future work" note — meaning the gate itself, and what would need to be true to remove it, is already documented.

## 4. The Mechanical Rule for Adding Future Documentation

When a genuinely new topic or product line arrives, follow this order — the same order used to create `12_Research` and `14_KnowledgeBase` in this V2 pass:

1. Add the new canonical document inside the *closest existing section* first (e.g., a new calculation feature goes into `02_Architecture/`, not a new section).
2. Cross-link it from every related existing document's "Related Documents" section (the convention already used throughout).
3. Add it to `docs/DocumentationIndex.md`'s table of contents and to the relevant Reading Path(s).
4. Add it to `14_KnowledgeBase/NorthstarEngineeringKnowledgeBaseV2.md`'s relevant Map section.
5. **Only promote to a new top-level numbered section once that topic has accumulated enough independent canonical documents (in practice, 3+) that nesting it under an existing section actively hurts navigability** — exactly the threshold Frontend, AI, and Database crossed in this pass.
6. Never rewrite or renumber an existing section to make room — append. `15_Mobile`, `16_Plugins`, etc. are valid future numbers; renumbering `01_Product` through `14_KnowledgeBase` should never be necessary again.

## 5. What This Explicitly Does Not Do

This document does not invent new architecture, endpoints, or schemas for Account Aggregation, Enterprise, Advisor, Mobile, or Plugin/SDK support — none of those are researched or designed yet, and inventing them here would violate the mission's own "never invent architecture" rule. It only records **where** each will go and **which existing design decisions already anticipate it**, so that when the real research and design work happens, it extends this documentation system instead of triggering another full restructuring.

---

## Related Documents
`01_Product/Roadmap.md` · `03_Engineering/ArchitectureDecisionRecords.md` · `07_AI/AIArchitecture.md` §6–10 · `09_Security/ThreatModel.md` · `14_KnowledgeBase/NorthstarEngineeringKnowledgeBaseV2.md` · `docs/DocumentationIndex.md`

## Related Tests
None — this is a structural/planning document with no code test surface.

---

*New synthesis document — no archived original; this is a V2-only deliverable (mission Step 12).*
