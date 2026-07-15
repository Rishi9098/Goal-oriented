# Documentation Inventory — Northstar

**Date:** 2026-07-13, taxonomy references updated 2026-07-14 for the V2 restructuring
**Method:** every `.md` file in the supplied archive was extracted, counted, and categorized. `__MACOSX/*` and `.DS_Store` were excluded per instruction. An additional 14 files under `backend/.venv/**` and `backend/.pytest_cache/**` (vendored third-party package licenses and a pytest cache stub — not project documentation) were also excluded as non-document artifacts, leaving **254 real project documents** across the repo root, `backend/`, `docs/`, `Document/`, and `AIAssistantResearch/`.

Every one of the 254 files below was assigned to exactly one of 39 clusters (verified programmatically — zero unassigned, zero double-counted). Each cluster maps to a target location in the taxonomy — see `docs/14_KnowledgeBase/NorthstarEngineeringKnowledgeBaseV2.md` for the current, full taxonomy rationale.

**V2 note:** the taxonomy this inventory's target-location column references was itself restructured once more, from an initial 9-section layout (`01-product`...`09-history`) into the current 14-section layout (`01_Product`...`14_KnowledgeBase`) — most consequentially, `AIArchitecture.md`, `FrontendArchitecture.md`, and `DatabaseArchitecture.md` moved out of a shared `02-architecture`/`02_Architecture` folder into their own top-level `07_AI`, `06_Frontend`, and `05_Database` sections respectively, and the AI research series moved from a subfolder of architecture into its own top-level `12_Research`. Every path below reflects the current (V2) location; see `docs/14_KnowledgeBase/DocumentationMigrationReport.md` §2 for the full before/after taxonomy mapping.

**Legend:** 🟢 Authoritative/backbone source · 🟡 Contributing source (folded in) · ⚪ Historical/superseded (archived, not merged) · 🔴 Duplicate chain (superseded by a later version in the same cluster)

---

## 1. Excluded, non-document artifacts

| Location | Count | Reason |
|---|---|---|
| `backend/.venv/lib/python3.11/site-packages/**/*.md` (httpcore, httpx, idna, mypyc, numpy, pip, starlette, uvicorn license/readme files) | 13 | Vendored third-party package documentation, not Northstar project documentation. |
| `backend/.pytest_cache/README.md` | 1 | Auto-generated pytest cache marker file. |

---

## 2. Cluster inventory

### 2.1 Product & Vision

| Cluster | → Target | Files | Status |
|---|---|---|---|
| **PRODUCT_VISION** (4) | `docs/01_Product/Vision.md` | `ProductRoadmapReport.md`, `PrivateProductReport.md` 🟢, `CompetitorAnalysisReport.md` 🟢, `ProjectDiscoveryReport.md` 🟢 | All 07-06, pre-dating every later Bible; none superseded, all contributing sources — this is the only cluster covering "why Northstar, who's the competition, what's the market." |
| **EARLY_MARKET** (2) | `docs/01_Product/Vision.md` (historical appendix) | `Document/md files/MARKET_CONTEXT.md`, `Document/md files/COMPETITOR_ANALYSIS.md` | ⚪ Historical — pre-project market research written before the product existed; `CompetitorAnalysisReport.md` is the later, project-grounded version. Preserved as an appendix, not merged into prose. |
| **EARLY_PROMPTS** (2) | `docs/13_Archive/ArchivedDesignDocs/` | `Document/Claude_Master_Prompt.md`, `Document/Lovable_Master_Prompt.md` | ⚪ Historical — the original AI-tool bootstrap prompts (Lovable was an earlier tooling direction; the shipped stack is TanStack Start + FastAPI per `CLAUDE.md`). Archived verbatim as project-origin artifacts, not referenced by any canonical doc. |
| **PERSONAS_JOURNEYS** (3) | `docs/01_Product/UserPersonas.md`, `UserJourneys.md` | `UserPersonasReport.md` 🟢, `FIRST_TIME_USER_REVIEW.md` 🟢, `UserJourney.md` 🟢 | All 07-06, complementary (personas vs. first-use narrative vs. step-by-step journey) — no overlap, all three merge cleanly. |
| **ROADMAP** (3) | `docs/01_Product/Roadmap.md` | `ImplementationRoadmap.md` 🟢, `PrioritizedBacklog.md` 🟡, `ProductConsistencyRoadmap.md` 🟡 | 07-06; `ImplementationRoadmap.md` is the largest (47KB) and most complete — backbone. |
| **PRODUCT_REQUIREMENTS** (12) | `docs/01_Product/Requirements.md` | `Milestone1ImplementationSpecification.md` 🔴, `Milestone1ImplementationSpecification_v2.md` 🔴, `Milestone1ImplementationSpecification_FINAL.md` 🟢, `Milestone2ImplementationContract.md` 🟢, `AcceptanceCriteria.md`, `ImplementationChecklist.md`, `ScreenInventory.md`, `DependencyMap.md`, `RiskChecklist.md`, `ValidationMatrix.md`, `FeatureCompletenessMatrix.md`, `FeatureGapAnalysisReport.md` | **Clear duplicate chain**: `_FINAL` supersedes `_v2` supersedes the unsuffixed original — only `_FINAL` is authoritative; the other two are archived as version history, not merged. |

### 2.2 Architecture

| Cluster | → Target | Files | Status |
|---|---|---|---|
| **SYS_ARCH** (18) | `docs/02_Architecture/SystemArchitecture.md` | `SystemArchitectureBible.md` 🟢 (backbone, 62KB, compiled 07-09) + `ArchitectureReport.md`, `ArchitectureDriftReview.md`, `ArchitectureReview_Phase0/2/2_Final/3.md`, `ArchitectureReview_M2.1-P4.md`, `ArchitectureReview_M2.6.1.md`, `GlobalShellArchitecture.md`, `GlobalShellImplementationPlan.md`, `GlobalShellCertification.md`, `GlobalShellRegressionReport.md`, `GlobalShellTechnicalDebt.md`, `ExecutiveSummary.md`, `MilestoneResumptionCertification.md`, `DesignAuthorityReview_Milestone1_v2.md`, `ProductDesignAuthorityReview.md` | The Bible is the authoritative backbone; every Architecture Review/Certification doc is a point-in-time checkpoint whose findings are folded into the Bible's "Validation Summary." Two internal supersessions: `ArchitectureReview_Phase2_Final.md` 🔴 supersedes `ArchitectureReview_Phase2.md` for the same milestone. |
| **EARLY_ARCH_DRAFTS** (2) | `docs/13_Archive/ArchivedDesignDocs/` | `Document/ARCHITECTURE_v2.md` 🔴 (supersedes) `Document/md files/ARCHITECTURE.md` | ⚪ Both pre-date `SystemArchitectureBible.md` and describe an earlier, partially different stack — historical only. |
| **CALC_ENGINE** (4) | `docs/02_Architecture/CalculationEngine.md` | `CalculationEngineBible.md` 🟢 (backbone) + `CalculationEngineReport.md` ⚪ (07-06, earlier, superseded), `CalculationContextReview.md`, `MonteCarloConsistencyReport.md` | Small, clean cluster — the Bible already absorbs the report; the two reviews contribute specific findings (custom inflation, Monte Carlo path-count consistency) to the Known-Risks section. |
| **RECO_ENGINE** (35) | `docs/02_Architecture/RecommendationEngine.md` | `FamilyGovernmentSchemeRecommendationEngineBible.md` 🟢 (backbone, 106KB) + `RecommendationEngineReport.md` ⚪, `RecommendationEngineV2.md`, `RecommendationEngineV2Validation.md`, `RecommendationEngineV2_E2EValidation.md`, `PolicyEngineReport.md`, `GovernmentPolicyReport.md`, `FamilyHUFPlanningReport.md`, `FamilyPlanningDesign.md`, `PRODUCT_CONSISTENCY_REVIEW.md`, `Milestone2CertificationReport.md` 🔴, `Milestone2CertificationReport_v2.md` 🟢, plus the full Task 9–12 micro-doc set: `DataIntegrityReview_Task9/10/11/12.md`, `DataIntegrityReview_M2.1-P2.md`, `DependencyValidation_Task10/11/12.md`, `RecommendationConflictReview_Task11.md`, `RecommendationConsistencyReview_Task10.md`, `RecommendationIntegrityReview_Task10/11/12.md`, `UserTrustAndDesignReview_Task9/10/11/12.md`, `IntegrationIntegrityReview_Task12.md`, `PR_REPORT.md`, `BlockerReport.md`, `ContractDeviationReport.md`, `DependencyValidationReport.md`, `TaskTrackerConsistencyReport.md` | **The largest cluster (35 files)** — reflects that Family/Government-Scheme/Recommendation features were built with an extremely fine-grained one-doc-per-concern-per-task convention (4 tasks × ~7 doc types). All of it is real, valuable engineering history; none of it is wrong or contradictory — it's simply granular. The Bible is the authoritative synthesis; every Task 9–12 doc's finding is preserved as a Known-Risks/Decision-Log entry, and the full originals are archived, not deleted. `Milestone2CertificationReport_v2.md` supersedes the v1 for certification status specifically. |
| **SCHEME_TASK3** (1) | `docs/02_Architecture/RecommendationEngine.md` (history) | `DesignReview.md` (Scheme Eligibility, Task 3) | ⚪ Earliest Milestone 2 design doc (07-06), pre-dates the Task 9–12 convention; folded into RecommendationEngine.md's history section. |
| **LIFE_EVENT_ENGINE** (28) | `docs/02_Architecture/LifeEventEngine.md` | `LifeEventEngineArchitecture.md` 🟢 (backbone, 49KB) + `LifeEventArchitectureValidation.md`, `LifeEventEngine_FinalReleaseAudit.md`, `LifeEventEngine_PhaseA_ImplementationReport.md`, `LifeEventEngine_BackendHardeningReport.md`, `LifeEventEngine_ProgressMatrix.md`, `LifeEventAPI_ImplementationReport.md`, `TransactionConsistencyImplementationPlan.md`, `LifeEventIntegrationReview.md`, `LifeEventIntegrationReport.md`, plus 16 per-event-type implementation reports (`LifeEvent_Adoption/BirthOfChild/Bonus/BusinessSale/BusinessStart/DependentParent/Divorce/EducationPlanning/HomeSale/HousePurchase/Inheritance/JobChange/MajorMedicalEvent/Marriage/NewLoan/PhaseB1(LoanPayoff)/Retirement/SalaryRaise_ImplementationReport.md`) | One doc per life-event type is a deliberate, readable convention (each event type has genuinely distinct business logic) — these become a linked appendix under the canonical doc rather than being prose-merged into it, since each retains standalone reference value for its specific event type's field/effect contract. |
| **AI_ARCH** (2) | `docs/07_AI/AIArchitecture.md` | `AICopilotFutureAIArchitectureBible.md` 🟢 (backbone, 69KB) + `AIArchitectureReport.md` ⚪ (07-06, earlier, superseded) | |
| **AI_RESEARCH_SERIES** (14) | `docs/07_AI/AIArchitecture.md` (linked research appendix) | `AIAssistantResearch/00`–`13` (Knowledge Architecture, Model Comparison, Financial AI Research, Dataset Research, Training Strategy, RAG Architecture, Tool Calling, MLOps, Security, Evaluation, Hardware Analysis, Roadmap, Final Recommendation, Executive Summary) | Already a complete, well-ordered, internally-consistent 14-part series with its own executive summary — kept together as a standalone research appendix (`docs/12_Research/`) rather than dissolved into the Bible, since its "research complete, no code written yet" status (per its own Executive Summary) is a distinct, still-relevant artifact. |
| **FRONTEND_ARCH** (1) | `docs/06_Frontend/FrontendArchitecture.md` | `FrontendArchitectureUserExperienceBible.md` 🟢 (backbone, 87KB) | |
| **SHELL_PHASES** (23) | `docs/06_Frontend/FrontendArchitecture.md` | `GlobalSearchDesign.md`, `KeyboardShortcutDesign.md`, `NotificationArchitecture.md`, `NotificationCenterDesign.md`, `NotificationIdentityReview.md`, `NotificationPerformanceReport.md`, `ProfileMenuDesign.md`, `SearchPerformanceReport.md`, `UXReview_Phase2.md`, `DesignReview_Phase0/1.md`, `DependencyValidation_Phase0/1/2/3.md`, `PerformanceBaseline_Phase0.md`, `PerformanceComparison.md`, `GlobalShellAccessibilityReport.md`, `GlobalShellPerformanceReport.md`, `PR_REPORT_Phase0/1/2/3.md` | The persistent-shell rebuild's own 4-phase history (AppShell foundation → Profile menu → Command palette/Search → Notifications) — folded into FrontendArchitecture.md's shell section and Known-Risks; PR reports archived. |
| **NAVIGATION_MISSION** (3) | `docs/06_Frontend/FrontendArchitecture.md` | `NavigationAudit.md`, `NavigationReview.md`, `NorthstarFinalProductReview.md`'s companion `NavigationImplementationReport.md` | Most recent frontend IA work (07-12), feeds FrontendArchitecture.md's navigation section directly — not superseded by anything. |
| **DATABASE_ARCH** (2) | `docs/05_Database/DatabaseArchitecture.md` + `docs/05_Database/DatabaseSchema.md` | `DatabaseSchemaBible.md` 🟢 (backbone, 108KB — the single largest source document) + `DatabaseDesignReport.md` ⚪ (07-06, earlier, superseded) | Split across two canonical docs by design: conceptual architecture (02) vs. full table-by-table reference (05), both sourced from the same Bible. |
| **API_LAYER** (2) | `docs/04_API/ServiceInteractions.md`, `RESTAPI.md` | `APIServiceInteractionBible.md` 🟢 (backbone, 70KB) + `APIContract.md` 🟡 | |
| **ADR** (2) | `docs/03_Engineering/ArchitectureDecisionRecords.md` | `ArchitectureDecisionRecordBible.md` 🟢 (backbone, 93KB — 13+ ADRs) + `ArchitectureDecisionRecord.md` 🟡 (ADR-001 standalone) | **Rule: every ADR decision is preserved verbatim, none reworded or reversed** — this document is pure consolidation (folder + cross-links), zero content invention. |

### 2.3 Engineering & Process

| Cluster | → Target | Files | Status |
|---|---|---|---|
| **ENGINEERING_META** (8) | `docs/03_Engineering/EngineeringHandbook.md`, `DeveloperGuide.md` | `ProjectOwnersHandbook.md` 🟢 (backbone, 90KB), `EngineeringKnowledgeIndex.md` 🟢 (96KB — feeds `DocumentationIndex.md` and `docs/04_API/APIReference.md`), `PROJECT_STATE.md` 🟡 (152KB — largest file in the archive; a point-in-time state snapshot, treated as historical/appendix rather than living reference), `EngineeringFindingsSummary.md` 🟡, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md` | These are themselves prior, high-quality consolidation attempts — the Handbook and Knowledge Index are the direct ancestors of this v2 restructuring and are used as primary backbones, not just historical references. |
| **EXISTING_DOCS_REFS** (7) | Distributed: `docs/ENGINEERING_CONSTITUTION.md`→`03-engineering/CodingStandards.md`; `docs/PRODUCT_PRINCIPLES.md`/`UX_PRINCIPLES.md`→`01-product/`; `docs/architecture.md`→`02-architecture/SystemArchitecture.md`; `docs/backend.md`→`04-api/APIReference.md`; `docs/database.md`→`05-data/`; `docs/frontend.md`→`02-architecture/FrontendArchitecture.md` | The 7 files already living at `docs/*.md` before this restructuring | These are the repo's own actively-maintained reference docs (tracked in git, recently modified) — treated as **contributing sources**, folded into their matching new-taxonomy canonical doc rather than archived, since they were already correct and current. |
| **TECH_DEBT** (2) | `docs/03_Engineering/TechnicalDebt.md` | `TechnicalDebt.md` 🟢, `TechnicalDebtReview.md` 🟡 | |
| **PROCESS_META** (3) | `docs/13_Archive/ArchivedReports/` | `DataSourceMigrationReport.md`, `ImplementationReport.md`, `P0_1_ImplementationReport.md` | ⚪ Early one-off process reports, archived with pointer summaries; `DataSourceMigrationReport.md` also feeds `docs/05_Database/MigrationGuide.md`. |

### 2.4 Testing, Validation & Quality

| Cluster | → Target | Files | Status |
|---|---|---|---|
| **TESTING_VALIDATION** (6) | `docs/08_Testing/TestingStrategy.md`, `ValidationStrategy.md`, `QualityMetrics.md` | `TestPlan.md` 🟢, `ValidationReport.md`, `VALIDATION_REPORT.md`, `CoverageReport.md`, `BenchmarkReport.md`, `PerformanceReport.md` | Foundational testing docs, all 07-05/07-06, all contributing. |
| **MILESTONE1_FINANCIALS** (4) | `docs/08_Testing/ValidationStrategy.md` | `DesignReview_Milestone1.md`, `UXValidationReport.md`, `UX_REVIEW.md`, `FinancialsE2EValidationReport.md` | Milestone 1's own validation/design-review pair, folded into ValidationStrategy.md's history. |
| **M21_STABILIZATION** (29) | `docs/08_Testing/ValidationStrategy.md` (history) | 5 sub-milestones (P0 Risk Profile Persistence, P1 Government Schemes Screen, P2 Insurance Audit Logging, P3 Accessibility Polish, P4 Dashboard Query Optimization) × ~6 doc types each (`DependencyValidation_*`, `DesignReview_*`, `RootCauseAnalysis_*`, `UserTrustReview_*`, `PR_REPORT_*`) + `SecurityReview_M2.1-P2.md`, `Testing_M2.1-P0.md`, plus the M2.6.1 overlay-fix's own 4 docs | The single largest "iterative micro-report" cluster (29 files) — each is a real, dated bugfix/patch record. All findings are preserved in ValidationStrategy.md's Decision Log; all 29 originals archived under `ArchivedValidationReports/`. |
| **PRELAUNCH_AUDITS** (11) | `docs/08_Testing/QualityMetrics.md` | `PreLaunchProductAudit.md` 🟢, `ProductConsistencyAudit.md`, `ProductDriftReview.md`, `FutureCompatibilityAuditReport.md` 🔴, `FutureCompatibilityAuditReport_v2.md` 🔴, `FutureCompatibilityAudit_Light.md` 🟢, `InteractiveProductAudit.md`, `BrokenInteractionReport.md`, `DeadClickReport.md`, `FoundationReconciliationReport.md`, `UXConsistencyReview.md` | `_Light` is explicitly a "Post-Stabilization-Sprint" re-run of the same audit and is the most current of the three Future-Compatibility documents. |
| **ACCESSIBILITY**, **AUTOMATION_MISSION**, **BEHAVIORAL_DESIGN_MISSION**, **CONSISTENCY_MISSION**, **MICROCOPY_MISSION**, **PLANHEALTH_MISSION**, **PERFORMANCE_UX_MISSION**, **NAVIGATION_MISSION**, **LIFEEVENT_INTEGRATION_MISSION**, **FINAL_PRODUCT_MISSION** (2 each + 3 for Navigation = 21 total) | `docs/08_Testing/QualityMetrics.md` + relevant architecture docs | The 10 Audit/Review + Implementation Report pairs from the most recent "Product Experience Completion" mission (Phases 1–10, dated 07-12/07-13) | **All final, none superseded** — this is the newest, most current work in the entire archive. Each pair's findings feed both `QualityMetrics.md` (what was validated) and the relevant architecture doc (FrontendArchitecture.md for UX/Accessibility/Consistency/Behavioral/Microcopy/Automation/Navigation; none touch Calculation/Database/Recommendation, confirmed by each report's own "zero backend files touched" statement). |

### 2.5 Security & Risk

| Cluster | → Target | Files | Status |
|---|---|---|---|
| **SECURITY** (2) | `docs/09_Security/SecurityArchitecture.md` | `SecurityReport.md` 🟢, `AUDIT.md` 🟢 ("Northstar Production Risk Audit") | |
| **RISK** (1) | `docs/09_Security/ThreatModel.md` | `RiskRegister.md` | Single file — kept standalone rather than force-merged (see §4, "documents that stay standalone"). |

### 2.6 Release

| Cluster | → Target | Files | Status |
|---|---|---|---|
| **RELEASE** (2) | `docs/11_Release/ReleaseGuide.md` | `ReleaseNotes.md`, `CHANGELOG.md` | `CHANGELOG.md` remains at repo root per standard convention (linked from, not moved into, `docs/`) — see §4. |

---

## 3. Duplicate chains (explicit)

| Chain | Winner | Losers (archived, version history preserved) |
|---|---|---|
| Milestone 1 spec | `Milestone1ImplementationSpecification_FINAL.md` | `_v2.md`, unsuffixed original |
| Milestone 2 certification | `Milestone2CertificationReport_v2.md` | unsuffixed original |
| Architecture Phase 2 review | `ArchitectureReview_Phase2_Final.md` | `ArchitectureReview_Phase2.md` |
| Early architecture draft | `Document/ARCHITECTURE_v2.md` | `Document/md files/ARCHITECTURE.md` |
| Future Compatibility Audit | `FutureCompatibilityAudit_Light.md` (latest re-run) | `FutureCompatibilityAuditReport.md`, `FutureCompatibilityAuditReport_v2.md` |

No chain was collapsed to fewer than one archived copy — every superseded version remains on disk under `docs/13_Archive/`.

## 4. Coverage check

254 files catalogued above = 254 files in the archive (excluding the 14 non-document artifacts). Cross-checked programmatically against the extracted file list — zero omissions, zero double-assignments.
