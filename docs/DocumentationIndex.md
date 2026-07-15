# Northstar Documentation Index

**This is the homepage of Northstar's documentation system.** Everything a new engineer, an AI agent, or a returning contributor needs to understand this platform lives under `docs/`, organized into 14 numbered sections plus a full historical archive. If you read nothing else, read this page and follow the reading path for your role below.

**How this system came to be:** this is the second restructuring pass of Northstar's documentation. The first (V1) consolidated 254 individual reports, audits, and reviews into 31 canonical documents across a 9-section taxonomy. This pass (V2) reorganizes those same 31 canonical documents into a 14-section taxonomy (splitting AI, Frontend, and Database into their own top-level sections; splitting Operations from Release; adding a dedicated Research section and a Knowledge Base section), corrects a real documentation-vs-implementation contradiction found along the way (§ below), and adds a Knowledge Preservation Matrix, a code-level Knowledge Graph, an Open Source Readiness review, and this expanded index. Nothing was deleted at either pass; every original is preserved under `docs/13_Archive/`. Full detail: `docs/14_KnowledgeBase/DocumentationMigrationReport.md`.

**A finding worth knowing before you read anything else:** every prior version of this documentation (and the original source material it was built from) claimed no CI/CD pipeline exists in this repository. This was false — `.github/workflows/ci.yml` has existed since the initial commit. It was corrected across every affected document during this V2 pass. This is flagged here first because it's the clearest demonstration of this system's own governing rule: **verify against the code, not against how many documents already agree with each other.**

---

## Complete Table of Contents

### 01_Product
- [`Vision.md`](01_Product/Vision.md) — what Northstar is, why it exists, competitive positioning
- [`Requirements.md`](01_Product/Requirements.md) — delivered milestone specs and acceptance criteria
- [`UserPersonas.md`](01_Product/UserPersonas.md) — the 11 personas this product is designed around
- [`UserJourneys.md`](01_Product/UserJourneys.md) — core flows and the full screen inventory
- [`Roadmap.md`](01_Product/Roadmap.md) — V2/V3/V4 and what's deliberately not sequenced yet

### 02_Architecture
- [`SystemArchitecture.md`](02_Architecture/SystemArchitecture.md) — the whole system's shape, tech stack, request lifecycles, CI/CD (corrected)
- [`CalculationEngine.md`](02_Architecture/CalculationEngine.md) — Monte Carlo, the Calculation Context, every real formula
- [`RecommendationEngine.md`](02_Architecture/RecommendationEngine.md) — Family, Government Schemes, Insurance, Recommendations (the largest single domain)
- [`LifeEventEngine.md`](02_Architecture/LifeEventEngine.md) — 18 life events, including a real NO-GO release audit and its remediation

### 03_Engineering
- [`EngineeringHandbook.md`](03_Engineering/EngineeringHandbook.md) — golden rules, feature playbooks, safe-modification guide, debugging guide
- [`DeveloperGuide.md`](03_Engineering/DeveloperGuide.md) — setup, git workflow, PR checklist
- [`CodingStandards.md`](03_Engineering/CodingStandards.md) — the 11-rule Engineering Constitution
- [`ArchitectureDecisionRecords.md`](03_Engineering/ArchitectureDecisionRecords.md) — ADR-001 through ADR-013, plus the incidents behind them
- [`TechnicalDebt.md`](03_Engineering/TechnicalDebt.md) — every known, verified debt item, by category

### 04_API
- [`RESTAPI.md`](04_API/RESTAPI.md) — all 61 endpoints, auth flow, validation pipeline
- [`ServiceInteractions.md`](04_API/ServiceInteractions.md) — cross-service call graph, read/write classification
- [`APIReference.md`](04_API/APIReference.md) — fast endpoint → service → table lookup

### 05_Database
- [`DatabaseArchitecture.md`](05_Database/DatabaseArchitecture.md) — the conceptual data model, relationships, lifecycle
- [`DatabaseSchema.md`](05_Database/DatabaseSchema.md) — all 36 tables, 11 migrations, CRUD matrix
- [`EntityRelationships.md`](05_Database/EntityRelationships.md) — cardinality and domain-cluster diagrams
- [`MigrationGuide.md`](05_Database/MigrationGuide.md) — how to write a schema migration, and how to migrate a consumer off a deprecated field

### 06_Frontend
- [`FrontendArchitecture.md`](06_Frontend/FrontendArchitecture.md) — routing, shell, state management, every frontend finding

### 07_AI
- [`AIArchitecture.md`](07_AI/AIArchitecture.md) — the current Copilot and the full proposed future AI roadmap

### 08_Testing
- [`TestingStrategy.md`](08_Testing/TestingStrategy.md) — philosophy, backend/frontend/accessibility/E2E approach
- [`ValidationStrategy.md`](08_Testing/ValidationStrategy.md) — the chronological record of every validation checkpoint this project ever ran
- [`QualityMetrics.md`](08_Testing/QualityMetrics.md) — current coverage, corrected feature-completeness matrix

### 09_Security
- [`SecurityArchitecture.md`](09_Security/SecurityArchitecture.md) — auth, authorization, rate limiting, the original 17-item risk audit and its resolutions
- [`ThreatModel.md`](09_Security/ThreatModel.md) — regulatory, security/privacy, data-correctness, and business risk

### 10_Operations
- [`OperationsRunbook.md`](10_Operations/OperationsRunbook.md) — weekly/monthly/quarterly/before-release/before-production checklists

### 11_Release
- [`ReleaseGuide.md`](11_Release/ReleaseGuide.md) — release process and pre-release checklist
- [`DeploymentGuide.md`](11_Release/DeploymentGuide.md) — what exists today (including the real CI pipeline), what a real deployment must still decide

### 12_Research
- [`ai-research series`](12_Research/) — the 14-part AI research series (linked appendix, kept intact) — start with `13_EXECUTIVE_SUMMARY.md`

### 13_Archive
- `ArchivedReports/`, `ArchivedAudits/`, `ArchivedImplementationReports/`, `ArchivedValidationReports/`, `ArchivedDesignDocs/`, `ArchivedPRReports/` — all 232 original documents, in full, organized by kind

### 14_KnowledgeBase
- [`NorthstarEngineeringKnowledgeBaseV2.md`](14_KnowledgeBase/NorthstarEngineeringKnowledgeBaseV2.md) — the master navigation document (start here if this index isn't enough)
- [`KnowledgePreservationMatrix.md`](14_KnowledgeBase/KnowledgePreservationMatrix.md) — every category of engineering fact, mapped to its canonical home
- [`KnowledgeGraph.md`](14_KnowledgeBase/KnowledgeGraph.md) — documents connected to services, tables, components, endpoints, tests, business rules
- [`DocumentQualityReview.md`](14_KnowledgeBase/DocumentQualityReview.md) — accuracy/completeness/freshness/maintainability/readability/authority scores for all 31 canonical docs
- [`DocumentationInventory.md`](14_KnowledgeBase/DocumentationInventory.md) — the full catalog of all 254 original documents
- [`DocumentationDependencyGraph.md`](14_KnowledgeBase/DocumentationDependencyGraph.md) — document-to-document relationships
- [`DocumentationMigrationReport.md`](14_KnowledgeBase/DocumentationMigrationReport.md) — the full record of both restructuring passes
- [`OpenSourceReadiness.md`](14_KnowledgeBase/OpenSourceReadiness.md) — is this repository ready to publish publicly?
- [`FutureCompatibilityDesign.md`](14_KnowledgeBase/FutureCompatibilityDesign.md) — where future product lines, SDK/plugins, and mobile land in this taxonomy without another rewrite
- [`QualityGateVerification.md`](14_KnowledgeBase/QualityGateVerification.md) — the final 15-point verification that no engineering knowledge was lost in this pass
- `NorthstarEngineeringKnowledgeBase_V1.md` — the superseded V1 master document, kept for history

### At the repository root (unmoved, by convention)
`README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `AGENTS.md`, `CLAUDE.md` — and `docs/ENGINEERING_CONSTITUTION.md`, `docs/PRODUCT_PRINCIPLES.md`, `docs/UX_PRINCIPLES.md` remain at their established paths since other documents reference them by exact location.

---

## Reading Paths

### New Engineer Onboarding (start here, ~1 hour)
1. `CLAUDE.md` (repo root, 5 min)
2. `03_Engineering/CodingStandards.md` (5 min)
3. `02_Architecture/SystemArchitecture.md` (15 min)
4. `02_Architecture/CalculationEngine.md` §1–2 (10 min)
5. `03_Engineering/EngineeringHandbook.md` §6 "Code Reading Guide" — follow its exact file-reading order for your first real hour in the source code

### Senior Backend Engineer
`02_Architecture/SystemArchitecture.md` §5–9 → `02_Architecture/CalculationEngine.md` → `02_Architecture/RecommendationEngine.md` → `02_Architecture/LifeEventEngine.md` (read §8 closely — a real NO-GO audit and its fix) → `04_API/ServiceInteractions.md` → `05_Database/DatabaseSchema.md` → `03_Engineering/ArchitectureDecisionRecords.md` in full

### Frontend Engineer
`06_Frontend/FrontendArchitecture.md` in full → `04_API/RESTAPI.md` (the contract it implements) → `03_Engineering/EngineeringHandbook.md` §2's frontend touch-points in each feature playbook → note FE-005 and FE-001 in `06_Frontend/FrontendArchitecture.md` §14 before touching Reports, Goals, Profile, or Copilot

### AI Engineer
`07_AI/AIArchitecture.md` in full (pay attention to the current/future split — §1–5 vs §6–10) → `12_Research/13_EXECUTIVE_SUMMARY.md` → `03_Engineering/CodingStandards.md` Rule 10 (the one rule every AI feature must honor) → `14_KnowledgeBase/KnowledgeGraph.md` §2 for exactly which services a future tool layer would wrap

### Security Engineer
`09_Security/SecurityArchitecture.md` in full → `09_Security/ThreatModel.md` → `02_Architecture/SystemArchitecture.md` §12 → `03_Engineering/TechnicalDebt.md` §Security

### QA Engineer
`08_Testing/TestingStrategy.md` → `08_Testing/ValidationStrategy.md` (the chronological record — read the Life Event Engine NO-GO row closely, it's the most instructive validation story in this project) → `08_Testing/QualityMetrics.md` → `14_KnowledgeBase/KnowledgeGraph.md` §2 for the business-rule-to-test-file traceability table

### Product Manager
`01_Product/Vision.md` → `01_Product/UserPersonas.md` → `01_Product/UserJourneys.md` → `01_Product/Roadmap.md` → `08_Testing/QualityMetrics.md` §2 for what's actually shipped vs. what a stale matrix once claimed

### Technical Writer / Documentation Maintainer
`14_KnowledgeBase/NorthstarEngineeringKnowledgeBaseV2.md` in full → `14_KnowledgeBase/DocumentationMigrationReport.md` → this index's own "One Rule for Using This System" below

### Recruiter
`01_Product/Vision.md` → `README.md` (repo root) → `14_KnowledgeBase/OpenSourceReadiness.md` for an honest picture of the codebase's public-readiness state

### Investor
`01_Product/Vision.md` → `01_Product/Roadmap.md` → `08_Testing/QualityMetrics.md` §4 (the most recent product-quality scorecard: 9/10, GO WITH MINOR CHANGES) → `09_Security/ThreatModel.md` §1 (regulatory risk, read this before any claim about "AI advisor" capability)

### Open Source Contributor
`14_KnowledgeBase/OpenSourceReadiness.md` first (know what's missing before you start) → `03_Engineering/DeveloperGuide.md` → `03_Engineering/CodingStandards.md` → `02_Architecture/SystemArchitecture.md`

---

## Search Guide

**Looking for a specific fact?** Start with `14_KnowledgeBase/KnowledgePreservationMatrix.md` — it maps every category of engineering knowledge (business rules, formulas, API contracts, security assumptions, etc.) to its canonical document directly, faster than searching document-by-document.

**Looking for why a decision was made?** `03_Engineering/ArchitectureDecisionRecords.md` — every ADR, plus the 4 real incidents that produced the project's most important lessons.

**Looking for whether something is still broken?** `03_Engineering/TechnicalDebt.md` (by category) or `08_Testing/QualityMetrics.md` §2 (corrected feature-completeness).

**Looking for a specific original report by name?** `14_KnowledgeBase/DocumentationInventory.md` catalogs all 254 by cluster and current location.

---

## The One Rule for Using This System

Every canonical document states its own **Last verified against code** date and, where relevant, corrects a stale claim it found in its own source material rather than silently repeating it. If you find a canonical document disagreeing with the current code, **the code wins** — update the document in the same change, per Coding Standards Rule 8. This is not a hypothetical: this exact V2 restructuring pass found and fixed a false "no CI/CD" claim that had been silently repeated across 5 documents and one prior restructuring pass. Verify; don't inherit.
