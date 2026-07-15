# Release Notes — Unreleased

**Date:** 2026-07-05
**Nature of this pass:** Bug-fix and code-quality validation. No new features, no architectural redesign, no refactor beyond what each fix required. Git operations are **not** performed — this file exists to prepare them for your review, per instructions.

---

## Executive Summary

Two sessions of work sit behind this release-notes file:

1. **A full end-to-end QA pass** (browser click-through of every user flow, live network/console/backend-log/database verification) found and fixed **4 real bugs**, one of which (a missing database migration) completely broke password reset, and another of which (a Profile-page bug) silently corrupted user data on unrelated saves.
2. **A backend architecture/type-safety validation pass** found and fixed **12 Ruff violations and 18 `mypy --strict` errors** that were present in the repository despite `pyproject.toml` already configuring both tools in strict mode — meaning they'd been accumulating unnoticed. All fixes are type-annotation, import, or formatting changes with zero runtime behavior difference, confirmed by an unchanged 164/164 test pass before and after.

The platform is in a materially better state than it started: the one HIGH-severity data-corruption bug and the one HIGH-severity broken-feature bug are both fixed and verified live; the backend's own strict quality gate (Ruff + mypy --strict + pytest) now actually passes, rather than silently not being enforced; and two pieces of documentation drift are corrected.

**Is it production-ready?** For this workload: yes, at 8/10 (see `VALIDATION_REPORT.md`'s Production Readiness Score for the detailed rationale) — contingent on the fixes in this changeset being merged. The main open, non-blocking gap is the complete absence of frontend automated tests (see `TechnicalDebt.md`), which is a process risk, not a live production risk.

---

## What Changed (grouped)

**Bug fixes (frontend + migration):**
- `backend/alembic/versions/004_password_reset_tokens.py` (new) — the missing migration that broke password reset
- `code/src/routes/app.profile.tsx` — stop silently corrupting `dependents`/`marital_status`
- `code/src/components/dashboard/GoalSimPanel.tsx` — wire up the dead "switch risk profile" button
- `code/src/routes/app.reports.tsx` — fix negative-currency formatting

**Type-safety / lint fixes (backend, zero behavior change):**
- `app/models/{user,goal,simulation}.py` — `TYPE_CHECKING`-guarded imports replacing silent `# type: ignore` comments
- `app/services/auth_service.py` — sealed `Any` leakage from `passlib`/`python-jose` at the boundary; added an `isinstance` check on the JWT `sub` claim (small security hardening, found as a side effect)
- `app/services/monte_carlo.py` — properly parameterized `npt.NDArray[np.float64]`
- `app/middleware/{request_id,rate_limit}.py` — corrected `call_next` parameter type to Starlette's actual `RequestResponseEndpoint`
- `app/middleware/auth.py` — explicit exception chaining (`raise ... from exc`)
- Assorted line-length wraps in `logging_config.py`, `schemas/simulation.py`, `services/planning_service.py`

**Documentation:**
- `docs/architecture.md` — corrected router list, table list, JWT-storage description, observability claim
- `CHANGELOG.md` — `[Unreleased]` section updated with a `### Fixed` block

**Reports generated (all at repo root):** `VALIDATION_REPORT.md` (browser/E2E QA pass), `ArchitectureReport.md`, `ImplementationReport.md`, `ValidationReport.md` (this session's architecture/type-safety pass), `PerformanceReport.md`, `SecurityReport.md`, `CoverageReport.md`, `BenchmarkReport.md`, `TechnicalDebt.md`.

---

## Validation Evidence

```
Backend:  ruff check app/        →  All checks passed!
          mypy --strict app/     →  Success: no issues found in 40 source files
          pytest -q              →  164 passed, 96.43% coverage (threshold 80%)
Frontend: tsc --noEmit           →  clean
          vite build             →  clean
          eslint (touched files) →  clean
```

---

## Suggested Commit

This changeset spans two logically distinct efforts (bug fixes vs. type/lint cleanup) touching overlapping files, so a single commit is reasonable here rather than splitting artificially:

```
fix: repair password reset, profile data corruption, and dead optimizer button; close backend Ruff/mypy --strict gaps

- Add missing password_reset_tokens migration (forgot-password was hard-broken)
- Fix Profile page silently overwriting dependents/marital_status on unrelated saves
- Wire up the non-functional "switch risk profile" optimizer suggestion
- Fix negative-currency formatting on the Reports page
- Resolve 12 Ruff violations and 18 mypy --strict errors in backend/app
  (forward-reference type hints, untyped-library boundaries, middleware
  parameter types) — annotation/formatting only, zero behavior change
- Correct 3 stale claims in docs/architecture.md

164/164 backend tests pass unchanged; frontend build/typecheck/lint clean.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

## Suggested Tag

Given `CHANGELOG.md`'s `[Unreleased]` section has never been cut to a version yet (no tags exist in this repo), and this changeset is fixes rather than new features:

```
v0.2.0
```

(Semantic Versioning: a `0.x` minor bump is appropriate for "still pre-1.0, meaningful fixes, no breaking API change" — there is no established `v0.1.x` tag to bump a patch from, since this repo has never been tagged.)

---

## Waiting For Your Confirmation

Per instructions, no commit, tag, or push has been made. Let me know if you'd like me to:
1. Commit with the message above (as-is or edited),
2. Tag `v0.2.0` after the commit, or
3. Hold off entirely.
