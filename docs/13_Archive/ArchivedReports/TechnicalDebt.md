# Technical Debt Register

**Date:** 2026-07-05
**Purpose:** A single consolidated list of every known, verified debt item in this repository as of today — carried forward from `AUDIT.md` (prior session) plus what this session's architecture/type-safety pass found. Each item has a verified source; nothing here is speculative.

---

## New Items Found This Session

### 1. No frontend automated test coverage — HIGH priority

**Evidence:** `code/package.json` has no test runner dependency; `find src -iname "*.test.*"` returns nothing. 11,035 lines of TSX/TS with zero automated coverage.
**Impact:** Today's Reports-page currency-formatting bug (see `VALIDATION_REPORT.md`) is exactly the class of bug a single unit test on `fmt()` would have caught before it ever reached manual QA.
**Recommendation:** Vitest + React Testing Library, starting with `lib/api.ts` mock-fallback branches and the currency formatters. See `CoverageReport.md` for detail.

### 2. Duplicate currency-formatting logic (frontend) — LOW priority, root cause of today's bug

**Evidence:** `code/src/lib/mock-data.ts` exports `formatCurrency()` (Intl.NumberFormat-based); `code/src/routes/app.reports.tsx` independently reimplements a local `fmt()` with different behavior instead of extending the shared one.
**Impact:** The two formatters drifted — one handled negative numbers correctly, the other didn't, until fixed this session.
**Recommendation:** Not merged in this pass (they serve different display needs — exact vs. abbreviated). Documented so the next engineer touching either one knows the other exists and checks for consistency. See `ArchitectureReport.md` §3.

### 3. Dead code: `create_tables()` / `drop_tables()` in `app/database.py` — LOW priority

**Evidence:** Defined, never called — not in the app lifespan (deliberately removed, AUDIT #7), not in any script, not in any test. Responsible for `database.py` sitting at 50% coverage (the only sub-90% file in the backend that isn't explainable by "untestable `__main__` block").
**Recommendation:** Either (a) wire into a documented dev entry point (e.g. a `make reset-schema-dev` target that's explicit about being a non-Alembic dev-only shortcut) and add one test each, or (b) delete them. Not done in this pass since neither option is required to fix a verified bug — flagging for a deliberate decision rather than silently picking one.

### 4. `docs/architecture.md` had 3 stale claims — FIXED this session

Router list, table list, and JWT-storage description were all out of date relative to code that's been shipped since. See `ArchitectureReport.md` §2 and `ImplementationReport.md` for detail. Listed here for completeness of the debt register, marked resolved.

---

## Carried Forward from `AUDIT.md` (prior session, still open — not touched this session, listed for a single source of truth)

| Item | Status | Why still open |
|---|---|---|
| #5 — No per-user cost cap on OpenAI Copilot endpoint | Partially fixed (timeout/retry done) | Needs a DB-backed counter or cache layer this project doesn't have yet |
| #11 — `conversation_id` accepted but never persisted (no multi-turn Copilot memory) | Deferred | Needs a new table/cache, token-budget truncation strategy, retention policy — a real feature, not a quick fix |
| #12 — In-memory rate limiter can't scale horizontally | Improved, not resolved | The attacker-amplified version (spoofing, unbounded memory) is fixed; the legitimate multi-instance limitation needs Redis, out of scope |
| #14 — Health check's `except Exception` doesn't page a human | Deferred | Needs an alerting backend (Datadog/PagerDuty/etc.) chosen first — the `/health` JSON body is already orchestrator-readable today |
| #15 — No email verification on registration | Deferred | Blocked on the same missing piece as #1: no email/SMS delivery provider integrated |

---

## Explicitly Not Debt (reviewed and confirmed correct, listed so it isn't re-flagged by a future pass)

- `AUDIT.md` #16 — `get_db`'s broad `except Exception: rollback` — this is correct session-dependency behavior, not masked error handling.
- The `cast()` calls added this session at the `passlib`/`python-jose` type boundary — standard, correct practice for sealing `Any` leakage from untyped third-party libraries; not a workaround to be "properly fixed" later.

---

## Summary Table

| Priority | Count | Items |
|---|---|---|
| HIGH | 1 | Frontend test coverage |
| MEDIUM | 0 | — |
| LOW | 2 | Duplicate formatting logic, dead `create_tables`/`drop_tables` |
| Carried forward (pre-existing, documented, deliberately deferred) | 5 | AUDIT #5, #11, #12, #14, #15 |

No CRITICAL debt found. The one HIGH item (frontend testing) is a real gap but not a ticking clock — it's a process gap, not a live production risk today.
