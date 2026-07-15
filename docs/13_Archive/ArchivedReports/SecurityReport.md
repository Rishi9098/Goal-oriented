# Security Report

**Date:** 2026-07-05
**Scope:** This session's type-safety pass plus a fresh review of authentication, authorization, secrets, and input validation in light of today's changes. Full historical security remediation lives in `AUDIT.md` (17 items, prior session) — this report does not re-litigate that, only confirms it still holds and adds what's new.

---

## Summary

No new vulnerabilities found this session. One small, genuine hardening was made as a side effect of fixing a `mypy --strict` error (see below). `AUDIT.md`'s prior fixes were spot-checked and confirmed still in place and not regressed by today's changes.

---

## Findings

### 1. JWT `sub` claim type confusion — HARDENED (minor, found while fixing an unrelated type error)

**Before:** `app/services/auth_service.py::get_user_id_from_token` did `user_id = payload.get("sub"); if not user_id: raise ValueError(...); return user_id` — since `payload` was an untyped `dict`, `user_id` was implicitly `Any`. A JWT with a non-string, truthy `sub` claim (e.g., a nested object, if an attacker could ever get a token signed with unusual claims, or if a future code path constructed a token differently) would pass the `if not user_id` check and be returned as if it were a valid user-ID string, to be used moments later in `uuid.UUID(user_id)` in `middleware/auth.py` — which would raise a generic, less-informative error rather than being rejected at the source with a clear reason.

**After:** `if not isinstance(user_id, str) or not user_id: raise ValueError("Token missing subject")`. This is a real (if narrow) defense-in-depth improvement, found only because fixing the `no-any-return` mypy error required removing the implicit `Any`.

**Severity:** Low — tokens are signed with this app's own `JWT_SECRET_KEY` (HS256), so an attacker would need the secret to forge a claim shape in the first place. Still a legitimate hardening, since "signed doesn't automatically mean shaped as expected" is exactly the class of assumption that's cheap to remove.

### 2. Confirmed still in place (no regression) — spot-checked against `AUDIT.md`

- httpOnly refresh-token cookie + CSRF double-submit (AUDIT #4) — `_cookie_kwargs()` and `_verify_csrf()` in `auth.py` unchanged.
- Rate limiter IP-spoofing protection via `trusted_proxy_ips` allowlist (AUDIT #2) — `middleware/rate_limit.py`'s `_get_client_ip` unchanged; only its `call_next` parameter's *type annotation* was corrected this session, not its runtime logic.
- Rate-limiter bucket LRU+TTL eviction (AUDIT #3) — unchanged.
- Password-reset token debug-gating (AUDIT #1) — unchanged; confirmed live in the preceding QA session (`reset_token` only present when `settings.debug` is true).
- Financial-input upper bounds against Monte-Carlo `inf`/`NaN` (AUDIT #10) — unchanged.
- Per-email forgot-password throttle (AUDIT #13) — unchanged.

### 3. Secrets

No hardcoded secrets found in any file touched this session. `.env.example` (not `.env`) is the only environment-variable template file under version control; `JWT_SECRET_KEY` is generated via `secrets.token_hex(64)` per `README.md`'s setup instructions. Confirmed no secret material appears in any of the 4 files modified this session (all are type-annotation/formatting-only diffs).

### 4. Injection / path traversal

Not applicable to today's changes — none of them touch file I/O, dynamic SQL construction, or user-supplied paths. All database access in the routers reviewed uses SQLAlchemy's parameterized `select()`/`.where()` — no raw string-interpolated SQL exists anywhere in the 9 routers read this session.

### 5. Sensitive logging

`app/logging_config.py` reviewed (touched this session for an E501 fix, formatting-only). No request bodies, tokens, or passwords are logged anywhere in the routers or middleware read this session — `middleware/rate_limit.py`'s warning log only includes `ip` and `path`, not headers or body content.

---

## Evidence

- Full diff of all files touched this session available via `git diff` — every change is either a type annotation, an import, a line-wrap, or the one `isinstance` narrowing described above.
- `AUDIT.md` items #1–#17 re-read in full this session as part of discovery; cross-referenced against current file contents for #1, #2, #3, #4, #10, #13 specifically (the ones most relevant to files touched today).

---

## Remaining Risks (carried over from `AUDIT.md`, unchanged by this session)

These are pre-existing, already-documented, already-triaged gaps — repeated here only so this report is a complete picture, not because they're new:

- No per-user cost cap on the OpenAI Copilot endpoint (AUDIT #5, partially fixed — timeout/retry done, cost cap deferred).
- In-memory rate limiter can't scale horizontally without Redis (AUDIT #12, documented limitation).
- No email verification on registration (AUDIT #15, blocked on missing email/SMS provider).
- Health-check's `except Exception` doesn't page a human on DB failure (AUDIT #14, deferred pending an alerting backend decision).

---

## Recommendations

1. No urgent action required — this session found nothing new and confirmed nothing regressed.
2. When the JWT/auth code is next touched for a feature reason, consider whether other `payload.get(...)` reads of JWT claims elsewhere in the codebase have the same "trust the shape" assumption `sub` had — a quick grep for `payload.get` found only the one site fixed here, but worth a second look if the token schema grows additional claims.
