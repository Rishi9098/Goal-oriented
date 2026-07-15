# Northstar Engineering Knowledge Base V2

**Status:** Canonical master navigation document · **Date:** 2026-07-14
**Relationship to other meta-documents:** `docs/DocumentationIndex.md` is the homepage (Table of Contents, Reading Paths, Search Guide, condensed) and should usually be read first. `14_KnowledgeBase/NorthstarEngineeringKnowledgeBase_V1.md` is the superseded predecessor, kept for history — it explains this system's *philosophy and maintenance process* (still current, still worth reading once) rather than duplicating its content here. This document is the **map layer**: one structured, fact-dense summary per domain, plus the Glossary, Engineering Timeline, and Future Vision the mission for this pass specifically requested.

**If you read exactly one document in this entire system, make it this one** — it is designed so a new engineer can understand the whole of Northstar by reading this page's Maps closely and following only the links each Map actually needs, rather than reading all 31 canonical documents cover to cover.

---

## 1. Overview

Northstar is a goal-based financial planning platform: users define financial goals, a real 10,000-path Monte Carlo engine computes a genuine probability of success for each one, and a family/India-specific recommendation layer (government schemes, insurance, tax-aware guidance) proposes what to do about it. An optional GPT-4o Copilot narrates already-computed data; it does not originate financial advice. Full detail: `01_Product/Vision.md`.

The codebase is a FastAPI (Python 3.12, async SQLAlchemy, Postgres) backend and a TanStack Start (React 19) frontend, developed against 673+ backend tests and a real, working (if incomplete) CI pipeline. Full detail: `02_Architecture/SystemArchitecture.md`.

This documentation system itself went through two restructuring passes: **V1** consolidated 254 original reports/audits/reviews into 31 canonical documents across 9 sections; **V2** (this pass) reorganized those 31 documents into 14 sections, corrected a real stale claim (a false "no CI/CD" assertion repeated across 5 documents), and added the Knowledge Preservation Matrix, Knowledge Graph, Open Source Readiness review, Future Compatibility Design, and this document. Full detail: `14_KnowledgeBase/DocumentationMigrationReport.md`.

## 2. Table of Contents

See `docs/DocumentationIndex.md` §"Complete Table of Contents" for the full, current list of all 31 canonical documents across all 14 sections plus the archive. Not duplicated here to avoid the two documents drifting out of sync with each other — update the Index, not this list, when a document moves.

## 3. Knowledge Map

The single fastest way to find *a specific fact* (a business rule, a formula, a security assumption) rather than a whole document: `14_KnowledgeBase/KnowledgePreservationMatrix.md`. It has one table per fact category (Architecture Decisions, Business Rules, Financial Formulas, API Contracts, Database Rules, Validation Rules, Testing Strategy, Security Assumptions, Performance Findings, Trade-offs, Known Bugs Resolved, Technical Debt Open, Rejected Ideas, Accepted Ideas/Product Philosophy, UX/Accessibility/Behavioral Findings, AI Findings, Future Research) mapping straight to a canonical document location. Use it before grep-ing through prose.

## 4. Architecture Map

| Subsystem | Canonical doc | Key fact |
|---|---|---|
| Whole-system shape, tech stack, request lifecycle, CI/CD | `02_Architecture/SystemArchitecture.md` | FastAPI + TanStack Start; CI (`ci.yml`) has existed since the initial commit — verified, not assumed, this pass. |
| Monte Carlo / calculation core | `02_Architecture/CalculationEngine.md` | 10,000-path log-normal simulation (`run_simulation()`), 2,000-path fast probe (`quick_probability()`) for the optimizer and inline goal refresh. |
| Family, government schemes, insurance, recommendations | `02_Architecture/RecommendationEngine.md` | The largest single domain; household modeling is an aggregator over existing tables, never an owner (ADR-002). |
| Life events (18 types) | `02_Architecture/LifeEventEngine.md` | Includes a real NO-GO release audit and its remediation — read §8 before assuming this engine is fully hardened. |
| Recommendation computation model | ADR-005 (`03_Engineering/ArchitectureDecisionRecords.md`) | Every recommendation is computed live, never persisted — independently re-derived four separate times across four domains without code reuse, strong evidence it's the right answer. |

## 5. API Map

| Concern | Canonical doc | Key fact |
|---|---|---|
| Full endpoint catalog, auth flow, validation pipeline | `04_API/RESTAPI.md` | 61 endpoints across all routers. |
| Cross-service call graph, read/write classification | `04_API/ServiceInteractions.md` | Every router calls exactly one primary service; routers themselves hold no business logic (Coding Standards). |
| Fast endpoint → service → table lookup | `04_API/APIReference.md` | The lookup table to use when you know the endpoint and need the service/table, not the narrative. |

## 6. Database Map

| Concern | Canonical doc | Key fact |
|---|---|---|
| Conceptual data model, relationships, lifecycle | `05_Database/DatabaseArchitecture.md` | Soft-delete is the rule for goals (`is_active = false`) — never a hard delete. |
| All tables and migrations | `05_Database/DatabaseSchema.md` | 36 tables, 11 migrations. |
| Cardinality, domain clusters | `05_Database/EntityRelationships.md` | Two FK-cascade behaviors specifically verified against real Postgres, not just the SQLite test backend (DB-011). |
| Writing a migration; retiring a deprecated field | `05_Database/MigrationGuide.md` | Deprecation is never complete until every frontend and backend consumer is migrated (Coding Standards Rule 11 — added after a real incident, ADR-004). |

## 7. Frontend Map

| Concern | Canonical doc | Key fact |
|---|---|---|
| Routing, shell, state management, every open finding | `06_Frontend/FrontendArchitecture.md` | FE-001: the Landing page claims account-aggregation/bank-linking that does not exist in the product — a known, tracked documentation/marketing defect, not a backend gap. |

## 8. AI Map

| Concern | Canonical doc | Key fact |
|---|---|---|
| Current Copilot + the full proposed future roadmap | `07_AI/AIArchitecture.md` | Strict current-vs-proposed split (§1–5 current, §6–10 proposed, explicitly labeled PLANNED NOT IMPLEMENTED) — the template every other document in this system follows for distinguishing shipped from aspirational. |
| Deep AI research (14-part series) | `12_Research/` | Kept as a linked appendix, not dissolved into `AIArchitecture.md` — start with `13_EXECUTIVE_SUMMARY.md`. |

## 9. Testing Map

| Concern | Canonical doc | Key fact |
|---|---|---|
| Philosophy and approach (backend/frontend/a11y/E2E) | `08_Testing/TestingStrategy.md` | No frontend automated test suite exists yet — a real, named gap, not an oversight hidden by omission. |
| Chronological record of every validation checkpoint | `08_Testing/ValidationStrategy.md` | The Life Event Engine's real NO-GO-then-remediated audit is the single most instructive validation story in this project's history. |
| Current coverage, corrected feature-completeness | `08_Testing/QualityMetrics.md` | 80% backend coverage gate, enforced automatically via `pyproject.toml`'s `addopts`, not an explicit CI flag. |

## 10. Security Map

| Concern | Canonical doc | Key fact |
|---|---|---|
| Auth, authorization, rate limiting, the original 17-item risk audit | `09_Security/SecurityArchitecture.md` | No dedicated security test suite — properties are verified per-domain (e.g., `TestCrossHouseholdOwnership` inside `test_family_router.py`). |
| Regulatory, security/privacy, data-correctness, business risk | `09_Security/ThreatModel.md` | Account Aggregation and the Explainable AI Advisor are both explicitly gated on named, unresolved regulatory questions — not vague "future work." |

## 11. Operations Map

| Concern | Canonical doc | Key fact |
|---|---|---|
| Weekly/monthly/quarterly/pre-release/pre-production checklists | `10_Operations/OperationsRunbook.md` | CI runs automatically on every push/PR; nothing in this runbook substitutes for verifying CI is green before a release checklist item is marked done. |

## 12. Release Map

| Concern | Canonical doc | Key fact |
|---|---|---|
| Release process, pre-release checklist | `11_Release/ReleaseGuide.md` | Assumes the full regression suite (`08_Testing/TestingStrategy.md`) has run clean. |
| What exists today vs. what a real deployment still needs | `11_Release/DeploymentGuide.md` | CI verifies (lint, typecheck, test, Docker build-check); nothing currently deploys — no frontend Dockerfile, no CD step. This is the corrected version of a claim every prior document got wrong. |

## 13. Archive Map

All 232 original documents live under `docs/13_Archive/`, organized into six subfolders by kind (`ArchivedReports`, `ArchivedAudits`, `ArchivedImplementationReports`, `ArchivedValidationReports`, `ArchivedDesignDocs`, `ArchivedPRReports`). Nothing was deleted at either restructuring pass. To find a specific original document by name, use `14_KnowledgeBase/DocumentationInventory.md`, which catalogs all 254 originals (254, not 232 — the remaining 22 became canonical documents' own direct source material and are cited in each canonical document's "Supersedes"/footer line rather than archived separately). Every archived document preserves its own Date/Purpose/Superseded-by/Reason-archived/Still-relevant fields per `14_KnowledgeBase/DocumentationInventory.md`'s own structure.

## 14. Reading Paths

Condensed here; full text with exact section numbers lives in `docs/DocumentationIndex.md` §"Reading Paths":

New Engineer · Senior Backend Engineer · Frontend Engineer · AI Engineer · Security Engineer · QA Engineer · Product Manager · Technical Writer/Documentation Maintainer · Recruiter · Investor · Open Source Contributor — eleven paths, one per role, each naming an exact ordered sequence of documents (and in several cases exact section numbers) to read.

## 15. Search Guide

Condensed here; full text in `docs/DocumentationIndex.md` §"Search Guide":

- A specific fact → `14_KnowledgeBase/KnowledgePreservationMatrix.md`
- Why a decision was made → `03_Engineering/ArchitectureDecisionRecords.md`
- Whether something is still broken → `03_Engineering/TechnicalDebt.md` or `08_Testing/QualityMetrics.md` §2
- A specific original report by name → `14_KnowledgeBase/DocumentationInventory.md`

## 16. Glossary

- **Calculation Context** — the five plan-input fields (`current_amount`, `monthly_contribution`, `target_date`, `risk_profile`, `target_amount`) whose change is the *only* trigger for goal probability recalculation (ADR-001). Everything else is a pure read.
- **Canonical document** — one of the 31 documents under `docs/01_Product` through `docs/11_Release`, `docs/12_Research` (as a kept appendix), and `docs/14_KnowledgeBase` (as meta-documentation) — the single authoritative source for its topic, superseding whatever originals fed into it.
- **Household as Aggregator** — ADR-002's foundational rule: the household/family model joins existing per-user tables; it never becomes a second owner of `goals`, `assets`, or any pre-existing row.
- **Live computation** — the pattern (ADR-005, ADR-006) of computing a value fresh on every read instead of persisting it, adopted independently four separate times in this codebase because it eliminates an entire class of staleness bug.
- **Quick probability** — the 2,000-path fast Monte Carlo probe (`quick_probability()`) used by the optimizer and inline goal refresh, distinct from the full 10,000-path `run_simulation()`.
- **Soft delete** — the mandatory pattern for goals: `is_active = false`, never a real `DELETE`. See `CLAUDE.md` and `05_Database/DatabaseArchitecture.md`.
- **Deprecation Completion (Rule 11)** — the Engineering Constitution rule, added after a real incident (ADR-004), that a deprecated field is not considered retired until every frontend and backend consumer has migrated off it.
- **FE-001 / FE-005** — tracked, numbered frontend findings in `06_Frontend/FrontendArchitecture.md` (FE-001: Landing page's false account-aggregation claim; FE-005: see the same document §14) — cite by number, not description, when discussing them elsewhere.

## 17. Engineering Timeline

A synthesized, chronological skeleton of this project's real engineering history, drawn from `ArchitectureDecisionRecords.md` and `ValidationStrategy.md` — not a new claim, a cross-referenced index into decisions already fully recorded elsewhere:

1. **Milestone 1** — initial household/family schema (ADR-002), `HUFEntity` shipped without its own financial data support (later found HIGH-severity, ADR-003).
2. **Foundation Reconciliation** — `huf_entity_id` nullable FK added (ADR-003); deprecate-in-place pattern established for superseded fields (ADR-004).
3. **Milestone 2 (Family Insurance/Recommendations)** — live-computation pattern for recommendations established (ADR-005), later independently re-derived three more times.
4. **Product Consistency Audit** — discovered the goal-probability staleness bug (a goal showing 3.8% and 5% in the same session) — the incident behind ADR-001.
5. **Stabilization Sprint** — ADR-001 shipped (recalculate only on Calculation Context change); Rule 11 (Deprecation Completion) added in direct response to the ADR-004 incident.
6. **Global Shell Phase 3** — notification markers pattern shipped (ADR-006), the fourth independent arrival at live-computation.
7. **Milestone 2.6.1 (Global Shell Certification)** — discovered and fixed the overlay mutual-exclusion bug (ADR-007) — 4 independently-built overlay states collapsed into one `activeOverlay` field.
8. **Life Event Engine release audit** — a real NO-GO finding and its remediation (`08_Testing/ValidationStrategy.md`, `02_Architecture/LifeEventEngine.md` §8) — the project's most instructive validation story.
9. **This documentation's own history** — V1 restructuring (254 → 31 canonical documents, 2026-07-13); V2 restructuring (14-section taxonomy, CI/CD claim correction, this document, 2026-07-14).

For the complete, unabridged decision catalog (ADR-001 through ADR-013+) with full context/alternatives/consequences for each, see `03_Engineering/ArchitectureDecisionRecords.md` directly — this timeline is a navigation aid, not a replacement.

## 18. Future Vision

Full detail in two dedicated documents rather than repeated here:

- **Product future** (what might get built, in what order, and why some things are explicitly *not* sequenced yet) — `01_Product/Roadmap.md`.
- **Documentation and architecture extensibility** (where future product lines, a public SDK, mobile apps, or an enterprise edition would land in the existing structure, and which architecture decisions already anticipate them) — `14_KnowledgeBase/FutureCompatibilityDesign.md`.

The short version: this documentation taxonomy and this codebase's own key extension points (the AI Tool-Calling/RAG scaffolding, the household schema's generality, the versioned per-domain API routers) were built so that the next several years of Northstar's growth extend this system rather than triggering a third full restructuring.

---

## Related Documents
`docs/DocumentationIndex.md` · `14_KnowledgeBase/NorthstarEngineeringKnowledgeBase_V1.md` · `14_KnowledgeBase/KnowledgePreservationMatrix.md` · `14_KnowledgeBase/KnowledgeGraph.md` · `14_KnowledgeBase/DocumentationDependencyGraph.md` · `14_KnowledgeBase/DocumentQualityReview.md` · `14_KnowledgeBase/OpenSourceReadiness.md` · `14_KnowledgeBase/FutureCompatibilityDesign.md` · `14_KnowledgeBase/DocumentationMigrationReport.md`

## Related Tests
None — this is a navigation document with no direct code test surface; see each linked Map row's own canonical document for its actual test cross-references.

---

*New synthesis document — mission Step 13 deliverable. Supersedes nothing directly; sits alongside `NorthstarEngineeringKnowledgeBase_V1.md` as the current master, per this document's own §1.*
