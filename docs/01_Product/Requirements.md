# Product Requirements

**Status:** Canonical · **Last verified against code:** 2026-07-06, cross-checked 2026-07-13
**Supersedes:** `Milestone1ImplementationSpecification_FINAL.md` (the winner of a 3-version duplicate chain — `_v2.md` and the unsuffixed original are archived as version history, not merged), `Milestone2ImplementationContract.md`, `AcceptanceCriteria.md`, `ImplementationChecklist.md`, `ScreenInventory.md` (cross-referenced from `docs/01_Product/UserJourneys.md`), `DependencyMap.md`, `RiskChecklist.md`, `ValidationMatrix.md`, `FeatureCompletenessMatrix.md` (superseded and corrected in `docs/08_Testing/QualityMetrics.md`), `FeatureGapAnalysisReport.md`.
**Note:** these are historical implementation specifications for already-delivered milestones — the *current, living* functional detail lives in the relevant architecture doc (Calculation Engine, Recommendation Engine, Life Event Engine); this document is the requirements-and-acceptance-criteria record, kept for traceability.

---

## Milestone 1 — Financial Profile Management (Delivered)

**Scope:** Income Sources, Expenses, Assets, Liabilities (full CRUD except type-change-after-creation, by design — to recategorize, delete and recreate), and Planning Assumptions (inflation rate, 3 expected-return tiers, retirement age, Social Security estimate, editable from one Settings form).

**A deliberate, verified property of this milestone:** none of the fields introduced here are read by the Monte Carlo simulation engine — confirmed then and re-confirmed now as the still-open architectural gap documented in `docs/02_Architecture/CalculationEngine.md` §8.

**Status:** ✅ Delivered, fully implemented per its own Definition of Done and Design Freeze checklist.

## Milestone 2 — Family Financial Planning (Delivered)

**Scope:** Household/member management, Government Scheme eligibility, Family Insurance tracking + 80D recommendation, Family Recommendations aggregation with conflict detection, Family Dashboard (6 cards). Delivered via a granular, per-task validation convention (Tasks 1–12), each independently reviewed for data integrity, dependency correctness, recommendation integrity, and user trust — the full record is in `docs/08_Testing/ValidationStrategy.md`.

**Status:** ✅ Delivered. Full business-rule detail: `docs/02_Architecture/RecommendationEngine.md`.

## Life Event Engine (Delivered, post-hoc-hardened)

**Scope:** 18 life event types, preview-before-commit, atomic multi-entity effects, guarded undo. Not part of either numbered milestone's original scope — added afterward, and the only requirement set in this document's history that shipped its engineering *before* its own release audit, which returned a NO GO (§ full story in `docs/02_Architecture/LifeEventEngine.md` §8) before the API/hardening work that followed closed every release-blocking finding.

**Status:** ✅ Delivered and hardened, confirmed via live grep this session.

---

## Feature Gap Analysis — Build Now / Later / Never (source of the current Roadmap)

Every item in `docs/01_Product/Roadmap.md`'s Version 2/3/4 traces to a build-now/later/never verdict originally argued for in this project's own gap-analysis pass — nothing on that roadmap is undebated. See `docs/01_Product/Roadmap.md` for the current sequencing; this document does not repeat it.

---

## Known Requirement-vs-Delivery Gaps (verified against current code)

See `docs/08_Testing/QualityMetrics.md` §2 for the corrected, current-state feature-completeness matrix — several items the original 07-08 matrix marked "missing" (Global search, Notification center, Profile avatar menu) are now complete; a smaller, still-genuinely-open set (email update, Dashboard goal-card click-through, Reports PDF export, AI mode disclosure, legal pages) remain gaps between what was originally scoped/implied and what shipped.

---

## Related Documents
`docs/01_Product/Roadmap.md` · `docs/08_Testing/ValidationStrategy.md` (the per-task validation record) · `docs/08_Testing/QualityMetrics.md` (current, corrected completeness) · `docs/02_Architecture/CalculationEngine.md`, `RecommendationEngine.md`, `LifeEventEngine.md` (living functional detail)


## Related Tests
`08_Testing/ValidationStrategy.md` (every Milestone's own validation checkpoint) · the archived Definition-of-Done and Design-Freeze checklists per milestone spec.

---

*Archived originals: `docs/13_Archive/ArchivedReports/Milestone1ImplementationSpecification_FINAL.md` (+ `_v2.md`, unsuffixed original — duplicate chain, version history preserved), `Milestone2ImplementationContract.md`, `AcceptanceCriteria.md`, `ImplementationChecklist.md`, `ScreenInventory.md`, `DependencyMap.md`, `RiskChecklist.md`, `ValidationMatrix.md`, `FeatureCompletenessMatrix.md`, `FeatureGapAnalysisReport.md`.*
