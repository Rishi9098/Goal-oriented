# Testing Strategy

**Status:** Canonical · **Last verified against code:** 2026-07-13 (673 backend tests passing, 97.89% coverage, confirmed by a fresh run this session)
**Supersedes:** `TestPlan.md` (archived), `ValidationReport.md`, `VALIDATION_REPORT.md`, `CoverageReport.md`, `BenchmarkReport.md`, `PerformanceReport.md` (all archived).

---

## 1. Philosophy

**Test-driven, coverage-gated, never adjusted to match a bug** (Coding Standards Rule 6). RED (failing test) → GREEN (minimal implementation) → IMPROVE (refactor without breaking tests). `pytest --cov=app --cov-fail-under=80` is a hard CI-equivalent gate, not an advisory report — verified passing at 97.89% as of the most recent full-suite run, well above the floor.

## 2. Backend Testing

**Framework:** `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`, no manual `@pytest.mark.asyncio` boilerplate) + `pytest-cov`.

**Test database:** an in-memory SQLite instance (`tests/conftest.py`'s `TestSessionLocal`) — a deliberate speed/isolation trade-off with one documented consequence: SQLite returns naive datetimes even for `TIMESTAMPTZ` columns, requiring an explicit `_aware()` normalization helper wherever code compares timestamps. **A handful of cascade/`SET NULL` guarantees rest on one-time manual verification against real Postgres, not continuous CI** (Coding Standards Rule 9's own named exception, DB-011) — know which claims in this codebase rest on that manual check versus automated coverage.

**Test types, per unit under test:**
- **Unit/property tests** — the Monte Carlo suite is the canonical example: every assertion is a range check, ordering check, or equality-under-fixed-seed check, never a comparison to an independently hand-calculated number — the correct choice for a stochastic engine, not a coverage gap (Coding Standards' own reasoning, preserved in `docs/02_Architecture/CalculationEngine.md` §6).
- **Integration tests** — every new endpoint requires at least one happy-path test, one test per validation error (422), one auth-failure test (401/403) (Developer Guide §2).
- **Boundary tests** — the exact-birthday pattern (SSY's 10th birthday, SCSS's 60th) is this codebase's own template for correctly testing a threshold, not an approximation.
- **Isolation tests** — every domain has at least one cross-user/cross-household isolation test confirming a mismatched owner gets 404, never a data leak.
- **Regression tests** — every discovered bug becomes a permanent test case (Coding Standards Rule 6's practical consequence); the red-team/incident-driven tests in `docs/03_Engineering/ArchitectureDecisionRecords.md`'s "Mistakes That Became Design Decisions" section are the clearest examples.

## 3. Frontend Testing

**No automated frontend test suite exists** — confirmed, unchanged, across every phase of this project's history through the most recent completion mission. Frontend correctness is verified by `tsc --noEmit`, `eslint`, `npm run build`, and manual/live browser verification — a deliberate, consistently-applied compensation pattern (every one of the most recent mission's 9 phase reports followed this identical validation sequence), not an oversight, though it remains the single longest-standing HIGH-priority item in `docs/03_Engineering/TechnicalDebt.md`.

**If/when a frontend suite is introduced:** Vitest + React Testing Library is the recommended starting point (per the earliest debt register's own recommendation), starting with `lib/api.ts`'s mock-fallback branches and the currency formatters — the exact class of bug (a Reports-page currency-formatting drift between two independently-implemented formatters) that a single unit test would have caught before manual QA.

## 4. Accessibility Testing

Per the project's own web-testing priority order: automated checks (axe-core or equivalent, zero "serious"/"critical" violations), keyboard-only navigation of every flow, screen-reader announcement verification (`role="status"`/`role="alert"` pairing, no double-announced decorative icons), and reduced-motion verification. The most recent completion mission's Phase 8 applied exactly this discipline to the three hand-rolled dialogs it fixed — see `docs/06_Frontend/FrontendArchitecture.md` §12.

## 5. E2E Testing

Playwright is the designated framework for critical user flows (onboarding, add-family-member, goal creation, life-event recording) — no committed E2E suite exists in this codebase as of this document's compile date; UI flows are currently verified live/manually per release, following the same compensation pattern as unit-level frontend testing.

---

## Related Documents
`docs/08_Testing/ValidationStrategy.md` (the historical validation-checkpoint record) · `docs/08_Testing/QualityMetrics.md` (coverage/benchmark numbers) · `docs/03_Engineering/CodingStandards.md` (Rules 6, 9)


## Related Tests
This document's own subject — see `08_Testing/ValidationStrategy.md` for the historical record and `08_Testing/QualityMetrics.md` for current numbers.

---

*Archived originals: `docs/13_Archive/ArchivedReports/TestPlan.md`, `ValidationReport.md`, `VALIDATION_REPORT.md`, `CoverageReport.md`, `BenchmarkReport.md`, `PerformanceReport.md`.*
