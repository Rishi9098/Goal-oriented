# Knowledge Preservation Matrix

**Date:** 2026-07-14
**Purpose:** every category of engineering fact this project has ever produced, mapped to the canonical document(s) that now carry it. This is the proof artifact for "no engineering knowledge was lost" — if a category below has no canonical home, that is a gap to close, not a fact to silently accept.

---

## 1. Architecture Decisions (ADRs)

| Fact category | Canonical home |
|---|---|
| ADR-001 through ADR-013 (full text, context, alternatives, consequences) | `03_Engineering/ArchitectureDecisionRecords.md` |
| The 4 "Mistakes That Became Design Decisions" narratives (PCA-3→ADR-001, PCA-2→Rule 11, Global Shell bug→ADR-007, the milestone-sequencing lesson) | `03_Engineering/ArchitectureDecisionRecords.md` |
| 11 "Future Decisions owed" (Portfolio Engine, Tax Optimizer, Estate Planning, HUF tax, Local Qwen, RAG, AI Agents, Mobile, Enterprise RBAC, Enterprise scale, Assumptions/Monte Carlo wiring) | `03_Engineering/ArchitectureDecisionRecords.md` §"Future Decisions" |

## 2. Business Rules

| Fact category | Canonical home |
|---|---|
| The full 51-rule Family/Recommendation business-rule catalog (BR-001–BR-051) | `02_Architecture/RecommendationEngine.md` §11 (highlights) + full text preserved in `13_Archive/ArchivedReports/FamilyGovernmentSchemeRecommendationEngineBible.md` §11 |
| 18 Life Event types' entity-effect contracts | `02_Architecture/LifeEventEngine.md` §5 + the 16 per-event-type archived reports (linked appendix, `13_Archive/ArchivedImplementationReports/`) |
| Calculation Context field list and recalculation trigger rule | `02_Architecture/CalculationEngine.md` §6 |
| Goal ownership vs. family-tagging distinction (never ownership-transferring) | `02_Architecture/RecommendationEngine.md` §4, `03_Engineering/ArchitectureDecisionRecords.md` (ADR-008) |

## 3. Financial Formulas

| Fact category | Canonical home |
|---|---|
| Every literal formula (compound growth, annuity FV, log-normal sampling + Itô correction, portfolio compounding, success rate/percentiles, plan health weighted average, savings rate, net worth) | `02_Architecture/CalculationEngine.md` §2 |
| 80D insurance deduction calculation (base limit, senior doubling, confidence tiers) | `02_Architecture/RecommendationEngine.md` §6 |
| Government scheme eligibility math (exact-calendar age, threshold rules) | `02_Architecture/RecommendationEngine.md` §5 |

## 4. API Contracts

| Fact category | Canonical home |
|---|---|
| All 61 endpoints (method, path, auth, purpose) | `04_API/RESTAPI.md` §2 |
| Auth flow, JWT structure, refresh/CSRF double-submit | `04_API/RESTAPI.md` §3, `09_Security/SecurityArchitecture.md` §1 |
| Validation pipeline (Pydantic → business → ownership → DB → response) | `04_API/RESTAPI.md` §4 |
| Cross-service call graph (every verified caller→callee edge) | `04_API/ServiceInteractions.md` §1 |
| Read/write classification per endpoint | `04_API/ServiceInteractions.md` §2 |

## 5. Database Rules

| Fact category | Canonical home |
|---|---|
| All 36 tables, 11 migrations, CRUD matrix | `05_Database/DatabaseSchema.md` |
| Relationships, cardinality, cascade behavior (`CASCADE` vs. the one `SET NULL`) | `05_Database/EntityRelationships.md`, `05_Database/DatabaseArchitecture.md` §2 |
| Migration-writing process + the deprecated-consumer-migration process (from the PCA-2 incident) | `05_Database/MigrationGuide.md` |
| 12 zero-consumer ("future runway") tables, why each exists | `05_Database/DatabaseArchitecture.md` §5 |

## 6. Validation Rules

| Fact category | Canonical home |
|---|---|
| Pydantic schema bounds (e.g. `_MAX_AMOUNT` guarding Monte Carlo from `inf`/`NaN`) | `02_Architecture/CalculationEngine.md` §3, `09_Security/SecurityArchitecture.md` §5 |
| Relationship-type-dependent field validation (Family module) | `02_Architecture/RecommendationEngine.md` §11 |
| The one database-level `CHECK` constraint (`nominees.percentage_share`) | `05_Database/DatabaseSchema.md` §4 (DB-010) |

## 7. Testing Strategy

| Fact category | Canonical home |
|---|---|
| TDD philosophy, coverage gate (80%, actually ~97.9%), backend/frontend/accessibility/E2E approach | `08_Testing/TestingStrategy.md` |
| Every validation checkpoint this project ever ran, chronologically, including the Life Event Engine's own NO-GO audit | `08_Testing/ValidationStrategy.md` |
| Current coverage numbers, corrected feature-completeness matrix | `08_Testing/QualityMetrics.md` |
| CI pipeline detail (jobs, what each verifies) — **new in V2**, corrected from a prior false "no CI" claim | `02_Architecture/SystemArchitecture.md` §4, `11_Release/DeploymentGuide.md` §1 |

## 8. Security Assumptions

| Fact category | Canonical home |
|---|---|
| Auth/session security, rate limiting, password/token handling, all 17 original risk-audit items and their fix status | `09_Security/SecurityArchitecture.md` |
| Regulatory, security/privacy, data-correctness, business/strategic risk register | `09_Security/ThreatModel.md` |

## 9. Performance Findings

| Fact category | Canonical home |
|---|---|
| Indexes, shared fetches, N+1 fixes, the one known unbounded-catalog-load bottleneck | `05_Database/DatabaseArchitecture.md` §4 |
| Frontend performance (shared React Query keys, lazy Palette queries, the 5 RQ-bypassing screens) | `06_Frontend/FrontendArchitecture.md` §10–11 |

## 10. Trade-offs

| Fact category | Canonical home |
|---|---|
| SQLite-tested vs. Postgres-deployed | `08_Testing/TestingStrategy.md` §2, `05_Database/DatabaseSchema.md` §4 (DB-011) |
| `VARCHAR` over `ENUM` for extensibility (ADR-009) | `03_Engineering/ArchitectureDecisionRecords.md` |
| Nullable sibling column over polymorphic owner model (ADR-003) | `03_Engineering/ArchitectureDecisionRecords.md` |

## 11. Known Bugs (Resolved)

| Fact category | Canonical home |
|---|---|
| The ADR-001 incident (Dashboard silently re-running Monte Carlo on every read) | `03_Engineering/ArchitectureDecisionRecords.md` §"Mistakes" |
| The PCA-2 incident (deprecated Profile fields still read+written) | `03_Engineering/ArchitectureDecisionRecords.md` §"Mistakes", ADR-004 |
| The Global Shell overlay bug (two overlays open simultaneously) | `03_Engineering/ArchitectureDecisionRecords.md` §"Mistakes", ADR-007 |
| Life Event Engine's field-scoped undo guard, idempotency gap, row-locking gap (all fixed, re-verified live) | `02_Architecture/LifeEventEngine.md` §8 |
| The V2 documentation CI/CD misconception (this restructuring's own catch) | `02_Architecture/SystemArchitecture.md` §4, `14_KnowledgeBase/DocumentationMigrationReport.md` |

## 12. Technical Debt (Open)

| Fact category | Canonical home |
|---|---|
| Full by-category debt register (architecture, calculation, frontend, life events, AI, performance, security, testing) | `03_Engineering/TechnicalDebt.md` |

## 13. Rejected Ideas

| Fact category | Canonical home |
|---|---|
| Genuine co-ownership for family-tagged goals (rejected, deferred as "Finding E") | `02_Architecture/RecommendationEngine.md` §4, ADR-008 |
| Persisted recommendations (rejected in favor of live computation, 4 independent times) | `03_Engineering/ArchitectureDecisionRecords.md` (ADR-005) |
| A general rule-interpreter for scheme eligibility (rejected — no premature abstraction) | `02_Architecture/RecommendationEngine.md` §5, ADR (Rule 7) |
| LangChain/LlamaIndex/CrewAI for the proposed AI tool layer (rejected — unnecessary framework surface) | `07_AI/AIArchitecture.md` §7 |
| Fine-tuning for knowledge injection (rejected — never for facts, only format/voice) | `07_AI/AIArchitecture.md` §8 |

## 14. Accepted Ideas / Product Philosophy

| Fact category | Canonical home |
|---|---|
| Product Principles #2/#7/#8, UX Principles #5/#7/#11 | `03_Engineering/CodingStandards.md`, `03_Engineering/EngineeringHandbook.md` §1 |
| Product Vision, competitive positioning, what Northstar deliberately is not | `01_Product/Vision.md` |
| The 11 personas and cross-persona patterns | `01_Product/UserPersonas.md` |

## 15. UX / Accessibility / Behavioral Findings

| Fact category | Canonical home |
|---|---|
| All 11 frontend findings (FE-001 through FE-011), including the still-open marketing-overclaim (FE-001) | `06_Frontend/FrontendArchitecture.md` §14 |
| Accessibility present/absent inventory (focus rings, ARIA, the 3 hand-rolled-dialog fix, still-open gaps: skip-link, live regions, contrast, reduced motion) | `06_Frontend/FrontendArchitecture.md` §12 |
| Behavioral design philosophy (celebration/supportive-note pattern, "never manipulate users") | Summarized in `06_Frontend/FrontendArchitecture.md`; full detail archived at `13_Archive/ArchivedAudits/BehavioralDesignAudit.md`/`BehavioralDesignImplementationReport.md` |

## 16. AI Findings

| Fact category | Canonical home |
|---|---|
| Current Copilot architecture, all 8 findings (AI-001–AI-008) | `07_AI/AIArchitecture.md` §4, §11 |
| Full future architecture (tool calling, RAG, fine-tuning, memory, safety/Truth Hierarchy, migration roadmap V1–V5) | `07_AI/AIArchitecture.md` §6–10 |
| The 14-part research series, kept intact | `12_Research/` (linked appendix) |

## 17. Future Research

| Fact category | Canonical home |
|---|---|
| Product roadmap V2/V3/V4, enterprise/advisor tracks (explicitly not sequenced) | `01_Product/Roadmap.md` |
| AI migration roadmap V1–V5 | `07_AI/AIArchitecture.md` §10 |
| Future compatibility design (plugins, SDK, mobile, enterprise) | `14_KnowledgeBase/NorthstarEngineeringKnowledgeBaseV2.md` §"Future Vision" |

---

## Coverage Self-Check

Every one of the 17 categories above has at least one canonical home — verified by construction (this matrix was built by walking each canonical document's own content, not guessed from category names alone). No category maps to "nowhere" or to only an archived, unmerged original.

---

## Related Documents
`DocumentationInventory.md` · `DocumentQualityReview.md` · `DocumentationDependencyGraph.md` · `NorthstarEngineeringKnowledgeBaseV2.md`
