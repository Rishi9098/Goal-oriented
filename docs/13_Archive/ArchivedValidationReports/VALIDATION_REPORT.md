# Northstar — End-to-End Validation Report

**Date:** 2026-07-05
**Scope:** Full-stack QA pass (backend contract, browser click-through, network/console/backend/DB validation, regression) treating the app as an unknown system prior to production deployment.
**Method:** Backend routers read in full to derive the real API contract; frontend `api.ts` and every route diffed against it; live click-through via Chrome MCP (browser automation) covering registration → onboarding → financials → goals → simulation → optimization → reports → copilot → settings → profile → logout/login → forgot/reset password; backend logs and PostgreSQL queried directly throughout; full backend test suite, frontend build, typecheck, and lint run as a regression gate.

---

## 1. Bugs Found (ranked by severity)

| # | Severity | Bug |
|---|----------|-----|
| 1 | **HIGH** | Missing Alembic migration for `password_reset_tokens` — forgot-password was completely broken against a properly-migrated database |
| 2 | **HIGH** | Profile page silently overwrote `dependents`/`marital_status` in the database on *any* unrelated save (e.g. just changing full name) |
| 3 | **MEDIUM** | Optimizer's "Switch to {risk profile}" suggestion was a non-functional decorative element — styled as an action but wired to nothing |
| 4 | **LOW** | Reports page rendered negative net worth as `$-149500` instead of `-$150k`, breaking the abbreviation/formatting used everywhere else on the page |

---

## 2. Root Causes

**#1 — `password_reset_tokens` table missing**
The `PasswordResetToken` SQLAlchemy model (`backend/app/models/reset_token.py`) was added and wired into `auth.py`'s forgot-password/reset-password endpoints, but no Alembic migration was ever written to create the table. It appears to have worked in earlier manual testing only because `create_tables()` (a `Base.metadata.create_all()` call in the app lifespan) was silently creating it — that call was correctly removed in an earlier remediation pass (AUDIT.md #7, fixing real schema-drift risk), which exposed this pre-existing migration gap. The backend's own test suite never caught this because its fixtures create the schema directly from SQLAlchemy metadata rather than running `alembic upgrade head`, so the gap only manifests against a database provisioned the documented way.

**#2 — Profile page data corruption**
`code/src/routes/app.profile.tsx` initialized its `household` form field to the hardcoded literal `"2 adults, 1 child"` and never called `api.getProfile()` to load the user's actual saved `dependents`/`marital_status`. Since `handleSubmit` always derives and sends `dependents`/`marital_status` from `form.household` on every save — including saves that only touched the name field — any profile save would silently reset the user's real household data back to whatever the hardcoded default implied (1 dependent, no marital status), regardless of what the user had actually entered during onboarding.

**#3 — Non-functional optimizer action**
`code/src/components/dashboard/GoalSimPanel.tsx` rendered the risk-profile-change suggestion as a `<span>` with pill/button styling and a `<ChevronRight>` icon, but no `onClick` handler and no call to `api.updateGoal`. It looked identical to an actionable control but was inert.

**#4 — Negative currency formatting**
`code/src/routes/app.reports.tsx`'s local `fmt()` helper checked `n >= 1_000_000` / `n >= 1_000`, both of which are false for any negative number, so negative values fell through to the raw `$${n.toFixed(0)}` branch, producing `$-149500` instead of a properly signed, abbreviated value.

---

## 3. Files Modified

| File | Change |
|------|--------|
| `backend/alembic/versions/004_password_reset_tokens.py` | **New** — migration creating `password_reset_tokens` (id, user_id FK, token_hash unique, expires_at, used_at, created_at) with matching indexes |
| `code/src/routes/app.profile.tsx` | Loads real profile via `api.getProfile()` in parallel with `auth.me()`; added `householdFromProfile()` to reverse-map `marital_status`/`dependents` into the existing household option strings so saves no longer corrupt real data |
| `code/src/routes/app.reports.tsx` | Fixed `fmt()` to handle negative numbers (sign extracted before magnitude-based abbreviation) |
| `code/src/components/dashboard/GoalSimPanel.tsx` | Wired the "Switch to {risk profile}" suggestion to a real `handleApplyRiskChange()` handler calling `api.updateGoal`, with loading state and error handling matching the rest of the component |

No backend router/schema/service code required changes — the API contract itself (Phase 2) matched the frontend client exactly across all 9 routers (auth, goals, dashboard, simulate, copilot, profile, financials, assumptions, reports); the "Notifications" and "Linked accounts" cards on the Settings page are intentionally inert "Coming soon" placeholders, not a mismatch.

---

## 4. API Mismatches Fixed

**None found.** A full static diff of `code/src/lib/api.ts` and every route file against the 9 backend routers (paths, methods, request/response schemas, status codes) showed complete alignment — the financials-path mismatch from a prior session's fix is holding, and no new drift was introduced. All mismatches found this session were frontend-only bugs (missing data hydration, missing event handler, missing negative-number branch), not contract drift.

---

## 5. Browser Validation Results

Exercised end-to-end via Chrome MCP (Computer MCP is capped at read-only tier for browsers by platform design, so Chrome MCP was used as the primary interaction tool per the standing instruction, with Bash reserved for servers/tests/logs/migrations):

| Flow | Result |
|------|--------|
| Landing page | PASS — loads clean, no console errors |
| Register (10-step onboarding, incl. income/expenses/assets/liabilities/goal/assumptions) | PASS — all 8 create/update calls returned correct 201/200 |
| Duplicate registration | PASS — correctly rejected with "Email already registered" (409) |
| Login | PASS |
| Login with wrong password | PASS — correctly rejected with "Invalid email or password" (401) |
| Dashboard | PASS — all figures cross-checked by hand (net worth, savings rate, monthly income/expenses) |
| Goals — Monte Carlo simulation | PASS — 10,000-path run returned consistent percentile data |
| Goals — Optimizer | PASS after fix — suggestions generated; "Switch to aggressive" now applies a real PATCH |
| Reports | PASS after fix — all stats match dashboard/goal data; negative net worth now formats correctly |
| AI Copilot | PASS — rule-based fallback responds correctly (no `OPENAI_API_KEY` configured, as expected) |
| Settings — change password | PASS (see network note below) — verified end-to-end via re-login with new password |
| Profile — edit | PASS after fix — real data loads and unrelated saves no longer corrupt it |
| Logout → Login | PASS |
| Forgot password → reset token → reset password → login | PASS after fix (was hard-broken before the migration) |

---

## 6. Backend Validation Results

- Backend log (`/tmp/dev_qa.log`) monitored throughout the session.
- One unhandled exception surfaced and fixed: `sqlalchemy.exc.ProgrammingError: UndefinedTableError: relation "password_reset_tokens" does not exist` (see Bug #1).
- No other unhandled exceptions, SQLAlchemy errors, or dependency-injection errors observed across the full click-through.
- **Tooling note:** the browser network-capture tool reported `503` for both `/auth/change-password` and (pre-fix) `/auth/forgot-password`. For change-password, the backend log showed a clean `COMMIT` + `204 No Content` for the exact same request, and the UI behavior (form cleared, no error banner) and a subsequent successful login with the new password confirmed the request actually succeeded server-side. This is very likely an artifact of the browser tool's request-capture timing on requests slowed by bcrypt hashing (~700ms), not a real application-level 503 — flagged here for visibility rather than treated as an app bug.

---

## 7. Database Validation

- Checked `password_reset_tokens` post-migration: correct schema, FK, and both indexes present.
- Orphan-record sweep across all 9 domain tables (`user_profiles`, `goals`, `income_sources`, `expenses`, `assets`, `liabilities`, `simulations`, `financial_assumptions`, `password_reset_tokens`) joined against `users`: **zero orphans**.
- QA test user's row counts cross-checked against UI actions taken: 1 goal, 1 income source, 2 assets (checking + brokerage), 1 liability — exact match.
- Directly reproduced and then verified the fix for the Profile-page corruption bug by round-tripping `dependents` through the UI (0 → corrupted to 1 → reset to 0 → confirmed it survives an unrelated save after the fix).

---

## 8. Test Results

| Check | Result |
|-------|--------|
| Backend `pytest` | **164 passed**, 96.42% coverage (threshold 80%) |
| Frontend `tsc --noEmit` | Clean |
| Frontend `vite build` | Clean |
| Frontend `eslint` (repo-wide) | 195 pre-existing violations, unrelated to this session's changes (confirmed via `git stash` diff — baseline already had 195; my changes added 2 more, both now fixed via scoped `eslint --fix` on only the 3 touched files) |
| Frontend `eslint` (3 files touched this session) | Clean |

---

## 9. Remaining Issues

- **Repo-wide Prettier/ESLint debt** (195 pre-existing violations across files untouched this session) — out of scope for this QA pass per minimal-diff discipline, but worth a dedicated formatting pass.
- **Browser network-capture tool showing spurious 503s** on slow (bcrypt-bound) requests — worth keeping in mind for future QA sessions so a real error isn't dismissed, or a false one isn't chased. Always cross-check against the backend log before trusting a browser-tool-reported status on a slow request.
- **"Risk profile" field on the Profile page has no backing model field** — there is no user-level risk-profile column in `UserProfile`; it's a local-only cosmetic default that's never persisted. Not a bug (nothing reads or corrupts it), but worth a product decision on whether it should exist at all or be removed until there's a real backing field.
- Notifications and Linked-accounts (Plaid) cards on Settings are intentionally unimplemented "Coming soon" placeholders — not a bug, just confirming they're not silently broken features.

---

## 10. Performance Observations

- Monte Carlo simulation (10,000 paths) and optimizer calls both returned in well under a second in this environment.
- `change-password` and `forgot-password` requests take ~700ms, dominated by bcrypt hashing — acceptable for auth-adjacent endpoints, but the cause of the network-tool artifact noted above.
- No N+1 query patterns or unbounded queries observed in the routers read during Phase 2.

---

## 11. Security Observations

- No new security issues found this session. Auth, CSRF, rate-limiting, and reset-token handling all matched the hardened behavior from the prior AUDIT.md remediation pass (httpOnly refresh cookie, CSRF double-submit, per-email throttle, debug-gated reset-token exposure).
- The Profile-page bug (#2) was a data-integrity bug, not a security bug — it could not be used by one user to affect another user's data, only their own.

---

## 12. Production Readiness Score

**8/10 — production-ready for this workload, contingent on merging the four fixes above.**

Rationale: the backend API contract is completely sound with zero frontend/backend drift; all 164 backend tests pass at 96% coverage; the one HIGH-severity bug found (missing migration) is now fixed and would have caused a hard failure of a core auth-adjacent feature (password reset) the moment this app was deployed against a freshly-migrated database, which is exactly how it would be deployed in any real environment. The second HIGH-severity bug (silent profile data corruption) is a genuine correctness issue that would have quietly degraded data quality in production without ever surfacing an error. Both are fixed and verified end-to-end. The two lower-severity issues (non-functional button, cosmetic formatting bug) are now also fixed. The remaining open item is pre-existing lint debt that doesn't affect runtime correctness.
