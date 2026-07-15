# Architecture Report

**Date:** 2026-07-05
**Scope:** Full-repository architecture discovery and boundary audit for Northstar.

---

## Summary

Northstar is a two-tier web application: a TanStack Start/React 19 SPA frontend (Bun) and a Python 3.12/FastAPI backend, communicating over a versioned REST API (`/api/v1`), backed by a single PostgreSQL 16 instance. There is no ADR directory, no roadmap document, and no git tags in this repository — the authoritative history of decisions lives in `AUDIT.md` (a prior security/production-readiness audit, 17 items, mostly fixed) and `CHANGELOG.md`. This report derives everything from the current state of the repo, not from assumptions carried over from any other session.

The architecture is sound and consistently applied: routers are thin, business logic lives exclusively in `services/`, models are the schema source of truth, and Pydantic schemas are the API contract. No layer violations, circular dependencies, or hidden coupling were found. Two documentation-drift items were found and fixed (see below). One dead-code item was found and is documented in `TechnicalDebt.md` rather than removed, since it isn't blocking anything.

---

## Findings

### 1. Module boundaries are clean and consistently enforced (evidence, no action needed)

```
backend/app/
├── models/      — SQLAlchemy ORM (schema truth)
├── schemas/     — Pydantic in/out models (API contract)
├── routers/     — HTTP handlers only — every router reviewed (9 files, ~500 LOC) contains
│                  zero business logic; each handler validates input, calls a service
│                  function, and returns a schema.
├── services/    — Business logic, no HTTP concerns (monte_carlo, optimizer,
│                  planning_service, auth_service)
└── middleware/  — auth, rate_limit, request_id — pure ASGI dependencies
```
Verified by reading every router in Phase 2 of this session's validation pass: `auth.py`, `goals.py`, `dashboard.py`, `simulate.py`, `copilot.py`, `profile.py`, `financials.py`, `assumptions.py`, `reports.py`. No exceptions found.

### 2. Documentation drift — FIXED

`docs/architecture.md` had three stale claims, all now corrected:
- Router diagram listed only 5 of the 9 actual routers (missing `profile`, `financials`, `assumptions`, `reports`).
- Table list showed 3 of the actual 9 tables (missing `user_profiles`, `income_sources`, `expenses`, `assets`, `liabilities`, `financial_assumptions`, `password_reset_tokens`).
- JWT section claimed both access **and** refresh tokens live in `localStorage`, and suggested moving to httpOnly cookies as a "future" step — this was already done (AUDIT.md #4, fixed 2026-07-05). Doc now accurately describes the current httpOnly-cookie + CSRF double-submit design.
- "Future Architecture" table's Observability row claimed "uvicorn logs" as current state; the repo actually already has structured JSON logging + request-ID correlation (`app/logging_config.py`, `app/middleware/request_id.py`) wired into `main.py`. Corrected.

### 3. Duplicate currency-formatting logic across the frontend (documented, not merged)

`code/src/lib/mock-data.ts` exports a shared `formatCurrency()` (Intl.NumberFormat-based, handles negatives correctly) used by the dashboard and goals pages. `code/src/routes/app.reports.tsx` independently implements its own local `fmt()` helper with different behavior (k/M abbreviation) instead of extending the shared one. This is exactly why the Reports page had a formatting bug this session (see `ValidationReport.md`) that the Dashboard page never had — the two pieces of logic drifted independently. Not merged in this pass (the two serve genuinely different display needs — exact vs. abbreviated — and merging them is a design decision, not a bug fix), but flagged here and in `TechnicalDebt.md` as the concrete mechanism behind today's bug class.

### 4. Dead code: `create_tables()` / `drop_tables()` in `app/database.py`

Defined, exported, but called from nowhere — not the app lifespan (removed deliberately per AUDIT #7), not any script, not any test. `backend/scripts/seed_data.py` only imports `AsyncSessionLocal`, not these functions. This is why `app/database.py` sits at 50% test coverage (lines 34-42, 46-47, 51-52 are exactly these two functions). See `TechnicalDebt.md` for the recommendation — not removed in this pass since it's inert, not broken.

### 5. No circular dependencies, no layer violations

Checked the model layer specifically since it's the one place forward references exist (`Goal` ↔ `User` ↔ `Simulation` relationships). These use string-quoted `Mapped["X"]` annotations with `TYPE_CHECKING`-guarded imports (added this session — see `ImplementationReport.md`), which is the correct pattern for SQLAlchemy's declarative relationship system and avoids any real circular import at runtime.

### 6. Dependency graph

Backend dependency direction is strictly `routers → services → models`, with `schemas` as a cross-cutting contract layer referenced by both routers and (for typed returns) services. Frontend dependency direction is `routes → components → lib/api.ts → lib/mock-data.ts`. No reverse dependencies found in either direction.

---

## Evidence

- All 9 backend routers read in full this session (Phase 2 of the QA pass) and cross-checked against `code/src/lib/api.ts` — zero path/method/schema mismatches.
- `git log`, `git tag -l`, `find . -iname "*ADR*"` all confirm: no tags, no ADRs exist in this repo.
- `grep -rn "create_tables\|drop_tables"` across `app/`, `tests/`, `scripts/` confirms zero call sites outside the definition.

---

## Remaining Risks

- The Reports-page-vs-shared-formatter duplication could recur in other pages that build their own local formatting helpers instead of extending `mock-data.ts`'s exports. No other instance found this session, but nothing structurally prevents it.
- No ADRs means architectural decisions (e.g., "why inline Monte Carlo instead of a worker queue") only live in prose inside `docs/architecture.md`'s "Design Decisions" section — sufficient today, but will not scale as a record once more than one or two people are making architectural calls.

---

## Recommendations

1. When adding new display-formatting logic, extend `mock-data.ts`'s exports rather than writing a page-local helper — this is the specific gap that produced today's bug.
2. Decide whether to keep `create_tables()`/`drop_tables()` as intentionally-dormant dev utilities (in which case wire them into a documented entry point, e.g. a `make` target) or remove them — see `TechnicalDebt.md`.
3. If the team grows past its current size, start a lightweight `docs/adr/` directory for future non-trivial architectural decisions rather than only capturing them in prose.
