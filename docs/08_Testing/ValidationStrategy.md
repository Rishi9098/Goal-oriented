# Validation Strategy — Historical Checkpoint Record

**Status:** Canonical · **Last verified against code:** 2026-07-13
**Supersedes:** the entire Milestone 1 Financials validation cluster (`DesignReview_Milestone1.md`, `UXValidationReport.md`, `UX_REVIEW.md`, `FinancialsE2EValidationReport.md`), the entire M2.1 stabilization cluster (29 files — `DependencyValidation_M2.1-P0`–`P4`, `DesignReview_M2.1-P0/1/3`, `RootCauseAnalysis_M2.1-P0`–`P4`, `UserTrustReview_M2.1-P0`–`P3`, `SecurityReview_M2.1-P2`, `Testing_M2.1-P0`, `PR_REPORT_M2.1-P0`–`P4`/`M2.6.1`), and the 10 Audit/Report pairs from the most recent Product Experience Completion mission.
**Purpose:** not a re-derivation of each checkpoint's findings (those live in the relevant architecture doc's own "Validation Summary" section) — this document is the chronological, cross-milestone record of *when* the project validated itself, *what method* it used each time, and *what the outcome* was.

---

## Validation Checkpoints, Chronologically

| Checkpoint | Scope | Method | Outcome |
|---|---|---|---|
| Milestone 1 (Financial Profile Management) | Design review, UX validation, E2E validation | Full design authority review + live UX walkthrough | Passed, with findings (marketing overclaims — FE-001 — trace back to this era) |
| Milestone 2 Task 1–8 (Family Financial Planning) | Data integrity, dependency validation, recommendation integrity, user trust & design review — per task | One review pass per concern per task (a deliberate, granular convention) | All passed; findings folded into `docs/02_Architecture/RecommendationEngine.md` |
| M2.1-P0 (Risk Profile Persistence Bug) | Dependency validation, design review, root cause analysis, user trust review, PR report | Full 5-document review cycle for a single bugfix | Fixed and verified |
| M2.1-P1 (Government Schemes Screen) | Same 5-document cycle | Same | Passed |
| M2.1-P2 (Insurance Policy Audit Logging) | Same cycle + a dedicated Security Review (the one sub-milestone with a standalone security pass) | Same | Passed |
| M2.1-P3 (Accessibility Polish) | Same cycle + a dedicated Accessibility Review | Same | Passed — the direct ancestor of the most recent mission's own Phase 8 |
| M2.1-P4 (Dashboard Query Optimization) | Same cycle + a dedicated Performance Review | Same | Passed — 25→22 queries measured, documented in `docs/02_Architecture/RecommendationEngine.md`'s Family Dashboard section |
| M2.6.1 (Overlay Mutual Exclusion Fix) | Dependency validation, architecture review, accessibility review, PR report | Same discipline applied to a cross-phase integration bug | Passed — produced ADR-007 |
| Global Shell Certification (Milestone 2.6, full) | Accessibility, performance, regression, technical debt — 4 dedicated certification documents | Live keyboard-only interaction, live network capture, cross-account isolation testing | **PASS** — the most comprehensive single certification pass in this project's history prior to the Life Event Engine's own audit |
| Life Event Engine — Final Release Audit | Architecture, product, UX, security, performance, recommendation, financial, data integrity, API, technical debt — 10 dimensions | Direct re-inspection of source, live test execution, grep-verified structural claims — explicitly re-verified every prior report's claim rather than taking it on faith | **NO GO** (4/10 overall) — zero API surface existed despite complete backend logic. Full detail and since-verified remediation: `docs/02_Architecture/LifeEventEngine.md` §8. |
| Life Event Engine — API + Hardening (remediation) | The 3 release-blocking findings from the audit above | Direct implementation + 10 new hardening-specific tests | All 3 release blockers resolved, independently re-confirmed via live grep this session |
| Northstar Product Experience Completion (Phases 1–10) | Navigation, Life Event integration, Plan Health UX, Microcopy, Automation, Consistency, Behavioral Design, Accessibility, Performance UX, Final Review | Audit-then-Implementation-Report pair per phase, live browser verification every phase, full backend suite re-run at the close | **GO WITH MINOR CHANGES** (9/10 overall) — 673/673 backend tests passing throughout, zero backend files touched across all 9 phases |

---

## The Recurring Method, Stated Once

Every checkpoint above follows the same underlying discipline, regardless of which era of the project produced it: **investigate before changing** (a dedicated review/audit document, often explicitly scoped as "investigation only, no code changed"), **verify against the actual running system** (live browser interaction, live network capture, or direct grep — never just re-reading a prior report's claim), and **write down what was found before writing down what was fixed**. This is why the archive contains as many *audit* and *review* documents as *implementation* documents — it is the project's own chosen quality process, not incidental sprawl.

---

## Related Documents
`docs/08_Testing/TestingStrategy.md` (the ongoing, per-commit testing approach) · `docs/08_Testing/QualityMetrics.md` (the numbers each checkpoint produced) · every `docs/02_Architecture/*.md` document's own "Validation Summary" section (the detailed findings behind each row above)


## Related Tests
Every backend test file referenced across every other canonical document — this document is the chronological index into when each was written and why.

## Related Validation Reports
This document's own subject — every validation checkpoint this project has ever run, archived in full under `13_Archive/ArchivedValidationReports/` and `ArchivedAudits/`.

## Related Implementation Reports
Cross-referenced per checkpoint in this document's own table.

## Related Future Work
A dedicated, Postgres-backed (not SQLite) integration test tier for FK cascade/`SET NULL` behavior (DB-011) · a committed CI-enforced coverage trend check beyond the bare 80% floor.

---

*Archived originals: the full Milestone 1 Financials cluster, the full M2.1/M2.6.1 stabilization cluster (29 files), the Global Shell Certification cluster, and the Life Event Engine's audit/hardening/API reports — see `docs/14_KnowledgeBase/DocumentationInventory.md` §2.4 for the complete file list.*
