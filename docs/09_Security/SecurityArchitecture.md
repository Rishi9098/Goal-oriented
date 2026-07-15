# Security Architecture

**Status:** Canonical · **Last verified against code:** 2026-07-05, cross-checked 2026-07-13
**Supersedes:** `AUDIT.md` ("Northstar Production Risk Audit," archived — the foundational 17-item risk audit), `SecurityReport.md` (archived).

---

## 1. Authentication & Session Security

JWT (HS256), two token types (access 30 min, refresh 7 days default), each carrying `sub`/`type`/`iat`/`exp`/`jti`. Refresh token delivered via an httpOnly cookie scoped to `/api/v1/auth`; a separate JS-readable CSRF cookie must be echoed as a header on refresh (double-submit, constant-time comparison via `secrets.compare_digest`). Every successful refresh rotates both the refresh token and CSRF pair, shrinking the replay window for a leaked token.

**Fixed since the original risk audit:** access and refresh tokens were originally both stored in `localStorage` — fixed 2026-07-05 to the current cookie-based scheme above.

## 2. Authorization

Purely ownership-based — **no role/permission (RBAC) system anywhere** in this codebase. Every authenticated user has identical capability over their own data, zero capability over anyone else's. Ownership is enforced by filtering `user_id`/household-ownership in the *same query* as the fetch, never a separate "fetch then check" step — a mismatched owner returns 404, never confirming a resource's existence to a non-owner.

## 3. Rate Limiting

An in-memory token-bucket limiter, IP-keyed, with an explicit trusted-proxy allowlist before honoring `X-Forwarded-For` (an untrusted client cannot spoof this header to bypass its own limit — fixed from an original unconditional-trust vulnerability). Tighter, path-specific buckets exist for `/auth/login`, `/auth/register`, `/simulate`; a separate per-email throttle exists for `/auth/forgot-password` specifically because the generic IP limiter alone can't stop a distributed attempt to mass-issue reset tokens for one target email.

**Known, documented limitation:** single-process, in-memory — will not correctly share limits across multiple workers or horizontal scale without a Redis-backed replacement (the limiter's own docstring states this explicitly).

**A real, still-open gap:** `/copilot` — the one endpoint with a genuine external per-call dollar cost — is **not** in the tightened-bucket list, unlike `/simulate` (a purely local compute cost). See `docs/07_AI/AIArchitecture.md` finding AI-004.

## 4. Password & Token Handling

Passwords hashed with bcrypt (`passlib`), never plaintext. Password reset tokens are stored as a SHA-256 hash (`token_hash`), never the raw value; the raw token is only ever returned in the response body when `settings.debug` is true (fixed from an original vulnerability where the plaintext reset token was returned unconditionally — full account takeover, fixed 2026-07-05). `/forgot-password` always returns 200 regardless of whether the email exists, preventing user enumeration.

## 5. Input Validation & Injection

Every write endpoint's body is a Pydantic schema with explicit bounds — e.g. `GoalCreate`'s upper bounds exist specifically to keep the Monte Carlo compounding loop away from `inf`/`NaN` territory (fixed from an original unbounded-input vulnerability). All database access uses SQLAlchemy's parameterized `select()`/`.where()` — no raw string-interpolated SQL exists anywhere in any router. No HTML/script sanitization library exists as a backend dependency — a low-risk gap given the current feature set stores no user-generated rich text (every free-text field is rendered as plain text), but a real, un-enforced absence, not a verified-safe design.

## 6. Data at Rest

**No encryption-at-rest or column-level encryption exists anywhere in this schema** — confirmed by the absence of any encryption library dependency. This includes `huf_entities.huf_pan` (a government tax ID, currently unused/zero-consumer) and every financial figure (income, asset value, liability balance), protected only by application-layer ownership checks, not database-level access control.

## 7. Audit Logging

Scoped to exactly 7 action types, all in the Family domain — Goals and Financials mutations produce zero audit trail at the database level, a real, open scope gap (not yet extended to the two domains most likely to also carry financial consequence).

## 8. CORS & Transport

An explicit origin allowlist (`cors_origins` in `config.py`), not a wildcard. HTTPS assumed at the deployment layer (no TLS termination logic in this codebase itself — a hosting-environment concern).

## 9. Fixed Since the Original Risk Audit (AUDIT.md, 17 items, 2026-07-05)

| # | Original finding | Resolution |
|---|---|---|
| 1 | `/auth/forgot-password` returned the plaintext reset token — full account takeover | ✅ Fixed — debug-gated only |
| 2 | Rate limiter trusted `X-Forwarded-For` unconditionally | ✅ Fixed — trusted-proxy allowlist added |
| 3 | Rate-limiter bucket dict never evicted — unbounded memory growth | ✅ Fixed — LRU+TTL eviction |
| 4 | JWT access **and** refresh tokens stored in `localStorage` | ✅ Fixed — cookie-based scheme (§1) |
| 5 | No rate limit or timeout on the Copilot endpoint | ⚠️ Partially fixed — timeout/retry done, cost cap still deferred (see AI-004 above) |
| 6 | Copilot had no error handling around the OpenAI call | ✅ Fixed |
| 7 | Startup ran `Base.metadata.create_all()` alongside Alembic — schema drift risk | ✅ Fixed |
| 9 | Monte Carlo simulations ran sequentially per goal, not in parallel | ✅ Fixed |
| 10 | No upper bound on financial input fields | ✅ Fixed (§5) |
| 13 | Password reset tokens had no rate limit on generation | ✅ Fixed (§3) |
| 17 | Build artifacts (`.output`, `.wrangler`, `.tanstack`) present in the working tree | ✅ Fixed |

## 10. Remaining Open Items (unchanged, carried forward honestly)

- #8 (no version control) — resolved by the project's own subsequent history; a point-in-time finding from before the repository existed as tracked.
- #11 — `conversation_id` accepted but never persisted (Copilot has no real multi-turn memory) — see `docs/07_AI/AIArchitecture.md` §5, AI-001.
- #12 — in-memory rate limiter cannot scale horizontally (§3 above).
- #14 — the health check's `except Exception` doesn't page a human on DB failure — deferred pending an alerting-backend decision.
- #15 — no email verification on registration — blocked on a missing email/SMS delivery provider.
- #16 — `get_db`'s broad `except Exception: rollback` — reviewed and confirmed **not** debt (correct session-dependency behavior), see `docs/03_Engineering/TechnicalDebt.md`.

---

## Related Documents
`docs/09_Security/ThreatModel.md` · `docs/02_Architecture/SystemArchitecture.md` §12 · `docs/05_Database/DatabaseArchitecture.md` §4 · `docs/07_AI/AIArchitecture.md` (AI-004) · `docs/03_Engineering/TechnicalDebt.md`


## Related Tests
No dedicated `test_security.py` file exists — security properties are verified per-domain (e.g. ownership isolation is tested inside `test_family_router.py`'s `TestCrossHouseholdOwnership`, not a separate security suite).

---

*Archived originals: `docs/13_Archive/ArchivedReports/AUDIT.md`, `SecurityReport.md`.*
