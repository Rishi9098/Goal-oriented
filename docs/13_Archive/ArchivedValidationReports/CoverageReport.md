# Coverage Report

**Date:** 2026-07-05
**Backend:** `pytest --cov=app --cov-report=term-missing` — 164 tests, 96.43% line coverage (threshold: 80%, `pyproject.toml`'s `--cov-fail-under=80`).
**Frontend:** No coverage figure exists — there is no test runner installed at all (see below).

---

## Backend Coverage — Full Breakdown

| Module | Stmts | Miss | Cover | Missing lines |
|---|---|---|---|---|
| `app/database.py` | 24 | 12 | **50%** | 34-42, 46-47, 51-52 |
| `app/main.py` | 46 | 11 | **76%** | 38-40, 77-85 |
| `app/logging_config.py` | 25 | 3 | 88% | 47-49 |
| `app/middleware/auth.py` | 20 | 2 | 90% | 30-31 |
| `app/routers/assumptions.py` | 36 | 3 | 92% | 59-61 |
| `app/routers/goals.py` | 60 | 4 | 93% | 46, 48, 96, 117 |
| `app/middleware/request_id.py` | 18 | 1 | 94% | 17 |
| `app/models/user.py` | 21 | 1 | 95% | 45 |
| `app/routers/financials.py` | 120 | 6 | 95% | 121, 197, 210-216, 249, 273 |
| `app/middleware/rate_limit.py` | 74 | 3 | 96% | 104, 120-121 |
| `app/models/goal.py` / `simulation.py` | 30 / 29 | 1 / 1 | 97% | 85 / 59 |
| `app/routers/auth.py` | 157 | 3 | 98% | 73, 200, 294 |
| Everything else (23 files) | — | 0 | **100%** | — |
| **TOTAL** | **1430** | **51** | **96.43%** | |

## Analysis of the Two Sub-90% Files

**`app/database.py` — 50%, lines 34-42 & 46-47 & 51-52.** These are exactly `create_tables()` and `drop_tables()` — the dead-code finding from `ArchitectureReport.md`/`TechnicalDebt.md`. Not a testing gap so much as a consequence of unused code existing at all; the fix is the same either way (wire them into a real entry point and test that, or remove them).

**`app/main.py` — 76%, lines 38-40 & 77-85.** Lines 38-40 are the lifespan-startup comment block explaining why `create_tables()` is no longer called (dead-adjacent, not executable logic worth testing). Lines 77-85 are the `if __name__ == "__main__":` uvicorn-run block — standard practice to leave untested since it's only exercised by literally running the file directly, which the test suite correctly doesn't do (it drives the app via `TestClient`/`AsyncClient` instead).

Both sub-90% files are therefore explainable and not a sign of undertested business logic — the actual business logic (routers, services, schemas) sits at 92-100% uniformly.

## Uncovered Lines Elsewhere (all ≥90%, minor)

- `middleware/auth.py:30-31` — the `except ValueError as exc: raise credentials_exc from exc` branch this session's B904 fix touched. Existing tests cover the 401 *outcome* of an invalid token but don't specifically assert the exception-chaining mechanics — low value to add given the outcome is already verified.
- `routers/goals.py`, `routers/financials.py`, `routers/assumptions.py` — small numbers of uncovered lines each, consistent with a handful of not-independently-tested branch combinations (e.g., a specific validation-error branch) rather than untested endpoints — every endpoint itself has at least one passing test.

---

## Frontend Coverage — None

**No test framework is installed.** `code/package.json` has no `vitest`, `jest`, or `@testing-library/*` dependency, and `find src -iname "*.test.*"` returns zero files. This is the single largest testing gap in the project — 11,035 lines of frontend TypeScript/TSX with zero automated test coverage, relying entirely on manual QA (as performed in the preceding session's `VALIDATION_REPORT.md`) to catch regressions.

This is not a new observation invented for this report — it's a direct, verifiable fact about the repo's current state, surfaced here because the task explicitly asked to detect missing tests.

---

## Recommendations

1. **Frontend:** stand up Vitest + React Testing Library (per this repo's own `rules/react/testing.md` convention already on file, just unused). Highest-value first targets: `lib/api.ts`'s mock-fallback branches (every function has an untested `BASE_URL ? real : mock` fork) and the currency-formatting helpers (`mock-data.ts`'s `formatCurrency`, `app.reports.tsx`'s `fmt`) — directly relevant given today's bug was in exactly this kind of untested pure function.
2. **Backend:** no urgent coverage work needed; the two sub-90% files are both explainable, not risky. If `create_tables()`/`drop_tables()` are kept per the `TechnicalDebt.md` recommendation, wire them into a documented entry point and add one test each — that alone would bring `database.py` to ~100%.
