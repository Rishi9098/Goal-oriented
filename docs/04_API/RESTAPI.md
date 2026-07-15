# REST API Reference

**Status:** Canonical · **Last verified against code:** 2026-07-09, updated 2026-07-13 for the Life Events endpoints (added since the source Bible)
**Supersedes:** `APIServiceInteractionBible.md` §1–3, §7–8 (archived in full), `APIContract.md`.
**Companion doc:** `docs/04_API/ServiceInteractions.md` (cross-service call graph, read/write classification, findings).

---

## 1. API Architecture

REST over HTTPS, JSON bodies, versioned under `/api/v1`. JWT access token in the `Authorization: Bearer` header; a separate httpOnly refresh-token cookie scoped to `/api/v1/auth`; a JS-readable CSRF cookie echoed back as a header on `/auth/refresh`.

## 2. Endpoint Inventory — 61 endpoints across 12 routers plus `/health`

*(56 endpoints at the source Bible's compile time; 5 more added since via the Life Event Engine.)*

### Authentication (10)
`POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` (refresh cookie + CSRF header), `POST /auth/logout`, `GET /auth/me`, `PUT /auth/me`, `DELETE /auth/me` (soft-deactivate), `POST /auth/forgot-password` (per-email rate-limited), `POST /auth/reset-password`, `POST /auth/change-password`.

### Goals (6)
`GET /goals`, `POST /goals` (triggers Monte Carlo), `GET /goals/{id}`, `PATCH /goals/{id}` (conditionally triggers Monte Carlo), `DELETE /goals/{id}` (soft-delete), `PUT /goals/{id}/family-tags`.

### Dashboard (1) · Simulation (2) · AI Copilot (1) · Profile (2)
`GET /dashboard`; `POST /simulate` (full 10k-path run), `POST /simulate/optimize`; `POST /copilot`; `GET /profile`, `PUT /profile` (upsert).

### Financials (14)
`GET/POST/DELETE /financials/income[/{id}]` (CRD, no U), `GET/POST/DELETE /financials/expenses[/{id}]` (CRD, no U — see API-002), `GET/POST/PATCH/DELETE /financials/assets[/{id}]` (full CRUD), `GET/POST/PATCH/DELETE /financials/liabilities[/{id}]` (full CRUD).

### Settings/Assumptions (2) · Reports (1)
`GET /assumptions` (lazily creates defaults), `PUT /assumptions`; `GET /reports/summary`.

### Family (13)
`POST /family/onboarding-seed`, `GET /family` (lazy-provisions), `POST /family/members`, `PUT /family/members/{id}`, `GET /family/members/{id}`, `DELETE /family/members/{id}` (soft), `GET /family/goals`, `GET /family/insurance`, `POST /family/insurance/policies` (no `DELETE` — API-004), `PUT /family/insurance/policies/{id}/coverage`, `GET /family/recommendations`, `GET /family/dashboard`, `GET /family/schemes`.

### Notifications (3)
`GET /notifications` (pure read, verified never-writing), `POST /notifications/{source}/{key}/read`, `POST /notifications/{source}/{key}/dismiss`.

### **Life Events (5) — new since the source Bible**
`POST /life-events` (record), `POST /life-events/preview`, `GET /life-events` (paginated history), `GET /life-events/{id}`, `POST /life-events/{id}/undo`. Full detail: `docs/02_Architecture/LifeEventEngine.md` §8.

### Utilities (1)
`GET /health` — no auth, excluded from rate limiting.

---

## 3. Authentication Flow

JWT (`sub`, `type`, `iat`, `exp`, `jti`). **The `jti` is generated but never checked against a revocation list** — a token remains valid until its own `exp` regardless of any account action (including `/auth/logout`, which only clears the refresh cookie; an already-issued access token stays valid up to its full lifetime).

Refresh: httpOnly cookie scoped to `/api/v1/auth`, paired with a JS-readable CSRF cookie echoed as a header (double-submit). The frontend's `apiFetch` de-duplicates concurrent 401-triggered refresh attempts into exactly one network call via a shared in-flight promise.

`middleware/auth.py`'s `get_current_user` is the single dependency every protected route uses — verified across all 61 endpoints, zero routes implement a bespoke auth check. Middleware order: `RateLimitMiddleware` → `RequestIDMiddleware` → `CORSMiddleware` — rate limiting runs *before* request-ID stamping, so a rate-limited request's logs won't carry a correlation ID (a minor, verified ordering consequence).

**Unprotected routes:** `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/forgot-password`, `/auth/reset-password`, `/health`.

---

## 4. Validation Pipeline

```
Request body → Pydantic schema validation → fails: 422 (automatic)
             → passes → Business validation (relationship-type rules, etc.) → raises ValueError: caught, re-raised as 422
             → passes → Ownership validation (same query as the fetch) → not found/not owned: 404
             → passes → Database validation (UNIQUE, the one CHECK constraint) → fails: 500, NOT gracefully mapped (a real, narrow gap — API-005)
             → passes → 200/201/204
```

---

## 5. Known Findings (API-001 through API-009)

| ID | Severity | Finding |
|---|---|---|
| API-001 | Medium | `/auth/logout` doesn't revoke the already-issued access token — valid up to 30 more minutes, no `jti` blocklist exists. A standard JWT trade-off, not flagged anywhere as a deliberate decision. |
| API-002 | Medium | `income_sources`/`expenses` lack `PATCH`, unlike `assets`/`liabilities` in the same router — a user must delete-and-recreate to fix an entry. |
| API-003 | Low | `/profile` 404s with no row; `/assumptions` lazily creates defaults — two structurally identical singleton endpoints behave differently on first access. |
| API-004 | Low | No `DELETE` for an insurance policy — a mistake can't be removed through the product. |
| API-005 | Low | Database-level constraint violations aren't caught/mapped to a `4xx` anywhere — a rare path could surface a bare `500`. |
| API-006 | Info (positive) | All 61 protected endpoints use the identical `get_current_user` dependency — a single, auditable authentication chokepoint. |
| API-007 | Info (positive) | `apiFetch`'s shared `_refreshPromise` correctly de-duplicates concurrent 401 refresh attempts. |
| API-008 | Info (positive) | `GET /dashboard` and `GET /reports/summary` are continuously, automatically verified to agree via a dedicated test — a real regression safety net. |
| API-009 | Info (positive) | `/health` is correctly excluded from rate limiting and auth, appropriate for a liveness probe. |

---

## Related Documents
`docs/04_API/ServiceInteractions.md` · `docs/02_Architecture/SystemArchitecture.md` §12 (Security Overview) · `docs/02_Architecture/LifeEventEngine.md` §8 (Life Events API detail, including the idempotency-key hardening this document's endpoint list doesn't repeat)

## Related APIs
This document is the endpoint catalog itself.

## Related Database Tables
Every table named in `docs/05_Database/DatabaseSchema.md` is reachable through one of these 61 endpoints.


## Related Tests
Every endpoint's own router-level test file (`backend/tests/test_*.py`, one per domain) — see `04_API/ServiceInteractions.md` for the service each endpoint calls into, and that service's own test file.

---

*Archived originals: `docs/13_Archive/ArchivedReports/APIServiceInteractionBible.md`, `APIContract.md`.*
