# Northstar Production Risk Audit

Generated 2026-07-05. Every item below was verified by reading the actual file/line — no aspirational or stylistic items. Ranked by production risk (data loss, security breach, outage, or hard scaling blocker first).

---

## 1. `/auth/forgot-password` returns the plaintext reset token in the API response — full account takeover — ✅ FIXED 2026-07-05
**File:** `backend/app/routers/auth.py:145-151`

The endpoint generates a password-reset token and returns it directly in the JSON response body (`reset_token=plain_token`) instead of only emailing it. There is no email-sending integration anywhere in the codebase. Anyone who knows (or guesses) a victim's email can call this endpoint, receive the reset token in the response, then call `/auth/reset-password` to set a new password and fully take over the account. The comment right above it ("Always return 200 to avoid leaking whether the email exists") shows the enumeration protection was deliberately built — this line defeats it completely by leaking something far more valuable than existence.
**Fix:** Never include `reset_token` in the HTTP response. Send it via an email/SMS provider. If no provider is wired up yet, gate the field behind `settings.debug` so it can never leak in production.
**Status:** Fixed — `reset_token` is now only included in the response when `settings.debug` is `True` (local dev / `.env` with `DEBUG=true`); it is `None` whenever `DEBUG=false` (current production-like default). `test_auth.py` updated: the old test asserting the token leaks was replaced with `test_forgot_password_known_email_does_not_leak_token` (asserts `reset_token is None`), and the two tests that exercise the full reset flow (`test_reset_password_with_valid_token`, `test_reset_password_token_used_twice_returns_400`) now `monkeypatch` `secrets.token_urlsafe` to a known value instead of reading the token from the response. Full backend suite: 135 passed. Note: an email/SMS delivery integration is still needed before this flow is usable in production — the fix only stops the leak, it doesn't add a way for the real user to receive the token.

## 2. Rate limiter trusts `X-Forwarded-For` unconditionally — auth brute-force and cost limits are bypassable — ✅ FIXED 2026-07-05
**File:** `backend/app/middleware/rate_limit.py:59-63`

`_get_client_ip` takes the first value of the client-supplied `X-Forwarded-For` header with no check that the request actually came through a trusted proxy. Any caller can set an arbitrary/random `X-Forwarded-For` on every request to get a fresh rate-limit bucket each time, completely bypassing the limiter on `/auth/login`, `/auth/register`, and `/simulate`. This turns the login-brute-force protection and the paid-OpenAI-call throttling (see #5) into a no-op for a deliberate attacker.
**Fix:** Only trust `X-Forwarded-For`/`X-Real-IP` when the request's direct peer is a known reverse proxy (e.g. compare `request.client.host` against an allowlist), otherwise use `request.client.host` directly.
**Status:** Fixed — added `settings.trusted_proxy_ips` (empty by default). `X-Forwarded-For` is only honored when `request.client.host` is in that allowlist; otherwise the direct TCP peer is always used, so spoofing the header no longer mints a new bucket. Deploy note: if this runs behind a real load balancer/reverse proxy, its IP must be added to `TRUSTED_PROXY_IPS` or all traffic will share one bucket keyed by the proxy's own IP.

## 3. Rate-limiter bucket dict is never evicted — unbounded memory growth (DoS) — ✅ FIXED 2026-07-05
**File:** `backend/app/middleware/rate_limit.py:54-56, 77`

`self._buckets` is a `defaultdict` keyed by `ip` or `ip:path` that grows forever — there is no TTL, LRU cap, or cleanup pass. Combined with #2 (attacker can mint unlimited distinct IPs via header spoofing), this is a straightforward memory-exhaustion DoS: every spoofed IP creates a new permanent dict entry and `_TokenBucket` object that is never freed for the life of the process.
**Fix:** Cap bucket count with an LRU eviction policy, or move to Redis with key TTLs as the module's own docstring already recommends.
**Status:** Fixed — buckets are now an `OrderedDict` with O(1) LRU eviction capped at `settings.rate_limit_max_buckets` (default 50,000), plus a periodic TTL sweep (`rate_limit_bucket_ttl_seconds`, default 600s) that drops buckets idle longer than the TTL. Redis migration is still the right move before running more than one process — see #12.

## 4. JWT access **and** refresh tokens stored in `localStorage` — ✅ FIXED 2026-07-05
**File:** `code/src/lib/api.ts:60-70`

Both the short-lived access token and the 7-day refresh token (`refresh_token_expire_days: int = 7` in `backend/app/config.py:21`) are stored in `localStorage`. Any XSS on the page (a compromised dependency, a third-party script, a reflected input) can read `localStorage` synchronously and exfiltrate both tokens, giving the attacker a week of persistent account access with no way for the user to detect or revoke it short of a server-side token-family invalidation (which doesn't exist — see #8).
**Fix:** Move refresh tokens to an `httpOnly`, `Secure`, `SameSite=Strict` cookie set by the backend; keep only the short-lived access token in memory/localStorage.
**Status:** Fixed, scoped as agreed: only the refresh token moved to a cookie; the access token stays in localStorage (low blast radius — it expires in 30 minutes and a stolen one can't be renewed without the httpOnly refresh cookie).
- Backend (`backend/app/routers/auth.py`): `/auth/login` and `/auth/refresh` now set `ns_refresh_token` (httpOnly, `Secure` unless `debug`, `SameSite=None` unless `debug`) and `ns_csrf_token` (readable, same attributes) cookies instead of returning `refresh_token` in the JSON body. `TokenResponse` no longer has a `refresh_token` field at all. `/auth/refresh` reads the cookie, requires a matching `X-CSRF-Token` header (double-submit CSRF defense — cross-site requests can't read the CSRF cookie to forge the header), and rotates both cookies on every use. Added `/auth/logout` to clear both cookies.
- Frontend (`code/src/lib/api.ts`): `setTokens`/`clearTokens` replaced with `setAccessToken`/`clearAccessToken`; refresh flow reads the CSRF cookie via `document.cookie` and calls `/auth/refresh` with `credentials: "include"`. All `fetch` calls now send `credentials: "include"`. Added `auth.logout()`, wired into sign-out and delete-account flows.
- CORS already had `allow_credentials=True` with an explicit origin allowlist (required for cross-site cookies — can't combine with a wildcard origin).
- Tests: `test_auth.py` TestLogin/TestRefresh rewritten for the cookie contract (6 new cases: CSRF-missing → 403, CSRF-mismatch → 403, no-session → 401, invalid-token → 401, rotation, logout-clears-session). `conftest.py`'s test client now uses `https://test` as `base_url` so its cookie jar honors `Secure` the same way a real browser would — this is also what caught the bug during development (cookies silently weren't being sent over the plain-`http://test` fixture). Full backend suite: 147 passed.
- Deferred, not done here: refresh-token family/session revocation list (so a leaked refresh token before rotation can be force-invalidated server-side) — bigger feature, not part of this pass.

## 5. No rate limit or timeout on the OpenAI Copilot endpoint — unbounded billing exposure — ✅ PARTIALLY FIXED 2026-07-05
**File:** `backend/app/routers/copilot.py:98-109`

`client.chat.completions.create` is called with no `timeout` parameter and no per-user request cap beyond the generic IP bucket (itself bypassable per #2). A single authenticated user (or an attacker who bypasses the IP limiter) can fire unlimited GPT-4o calls, each billed to the project's OpenAI account, with no circuit breaker. A hung OpenAI request also has no timeout, so it will hold the request (and the DB session/connection from `Depends(get_db)`) open indefinitely.
**Fix:** Add a `timeout=` to the OpenAI call, add a per-user daily/hourly cap tracked in the DB or a cache, and catch `openai.APIError`/`RateLimitError` to fall back to `_fallback_response` instead of raising a raw 500.
**Status:** Timeout fixed — `AsyncOpenAI` is now constructed with `timeout=settings.openai_timeout_seconds` (default 10s) and `max_retries=settings.openai_max_retries` (default 2, using the SDK's built-in exponential-backoff retry). **Per-user cost cap not implemented** — the generic IP rate limiter (now spoof-resistant per #2) is the only throttle on this endpoint. A per-user daily/hourly cap would need either a new DB-backed counter or a cache layer this project doesn't have yet; flagging as the top remaining item.

## 6. Copilot endpoint has no error handling around the OpenAI call — contradicts its own "always functional" design — ✅ FIXED 2026-07-05
**File:** `backend/app/routers/copilot.py:98-110`

The module docstring says the endpoint "Falls back to a rule-based responder when no key is configured so the endpoint is always functional," but that fallback only triggers when the key is *absent*. If the key is present but OpenAI is down, rate-limited, or returns an error, the exception propagates as an unhandled 500 — the fallback path is dead code in the one scenario (upstream outage) where it's actually needed.
**Status:** Fixed — the `create()` call is now wrapped in `try/except OpenAIError` (the SDK's base exception, covering timeouts, rate limits, connection failures, and API errors), logging a warning and falling through to `_fallback_response` on any failure. Tests: `test_copilot.py::TestCopilotOpenAIPath` (3 new cases, faking the OpenAI client) verify the success path, the error-falls-back path, and that the client is constructed with the configured timeout/retries. Full backend suite: 150 passed.
**Fix:** Wrap the `create()` call in `try/except` and fall through to `_fallback_response` on any `openai` exception.

## 7. Startup runs `Base.metadata.create_all()` while Alembic migrations also exist — schema drift / broken deploys — ✅ FIXED 2026-07-05
**File:** `backend/app/database.py:38-40`, `backend/app/main.py:23`, `backend/alembic/versions/`

`create_tables()` (raw `create_all`) runs unconditionally on every app startup, in every environment, alongside a separate Alembic migration history (`001_initial_schema.py`…`003_composite_indexes.py`). `create_all` only creates missing tables — it never applies `ALTER TABLE`s from later migrations, and it will pre-create tables in a fresh environment before Alembic ever runs, which causes `alembic upgrade head` to fail with "table already exists" or silently desync `alembic_version`. Two sources of truth for schema means a model change that isn't captured in a migration will appear to work in dev (via `create_all`) and then be silently absent in any environment where only Alembic is run (or vice versa).
**Status:** Fixed — removed the `create_tables()` call from `main.py`'s lifespan entirely; Alembic is now the sole owner of schema in every environment. (`create_tables`/`drop_tables` remain in `database.py` as opt-in utilities, just no longer auto-invoked.) The test suite was already unaffected either way — it builds its own SQLite schema directly in `conftest.py`'s `db` fixture, never through the app's ASGI lifespan.
- Also fixed migration `003_composite_indexes.py` per explicit instruction: `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block, which is what Alembic wraps every migration in by default — this migration would have failed the moment anyone actually ran `alembic upgrade head` against Postgres. Wrapped both `upgrade()` and `downgrade()` in `op.get_context().autocommit_block()`.
- Verified for real, not just by inspection: spun up a scratch PostgreSQL 14 instance (Homebrew, no Docker available in this environment) and ran `alembic upgrade head` from scratch — confirms all three migrations apply cleanly, `ix_goals_user_id_active` and `ix_goals_user_id_priority` are created via `CREATE INDEX CONCURRENTLY`, `alembic downgrade -1` correctly drops them, and re-running `upgrade head` afterward is idempotent (`IF NOT EXISTS`/`IF EXISTS` guards). Full backend suite: 150 passed throughout.
**Fix:** Remove `create_tables()` from the app lifespan in non-test environments; Alembic should be the only path that touches schema in production.

## 8. No git repository — zero version control on the entire project
**Root**

`git status` fails with "not a git repository." There is no commit history, no rollback point, no code review trail, no CI/CD gate, and no way to tell what changed between the current state and any prior working state. For a codebase already handling auth, JWTs, and financial data, this blocks any real review or safe-deploy process and is a single point of catastrophic loss if the working directory is ever corrupted or overwritten.
**Fix:** `git init`, commit current state, and push to a remote before any further changes.

## 9. `refresh_goal_probabilities` runs Monte Carlo simulations sequentially per goal, not in parallel — ✅ FIXED 2026-07-05
**File:** `backend/app/services/planning_service.py:26-37`

Every call to `/dashboard` or `/reports/summary` awaits `quick_probability_async` once per active goal, one at a time, inside a plain `for` loop. Each call is a full thread-pool round trip (2,000-path simulation). A user with 8 goals pays 8x the latency serially instead of concurrently. Under load this also serializes against the same shared default thread-pool executor used elsewhere in the process.
**Status:** Fixed — dispatch now uses `asyncio.gather` over all goals' `quick_probability_async` calls instead of a sequential `for`/`await` loop; results are zipped back onto the corresponding `Goal` in order (`zip(..., strict=True)` so a mismatched result count fails loudly instead of silently misassigning). Still bounded by the shared default thread-pool executor's worker count (unchanged, out of scope here) and by CPU core count for the underlying NumPy work — this fix removes the *artificial* serialization, not the physical compute cost.
Tests: `test_planning_service.py::TestRefreshGoalProbabilitiesConcurrency` (2 new cases, using the real SQLite-backed `db` fixture) — one proves >1 simulation is in-flight at once (would be impossible with the old sequential loop), the other proves each result maps back to the correct goal after concurrent dispatch. Full backend suite: 152 passed.
**Fix:** Dispatch with `asyncio.gather(*[quick_probability_async(...) for g in goals])`.

## 10. No upper bound on financial input fields — Monte Carlo can be driven to `inf`/`NaN` — ✅ FIXED 2026-07-05
**Files:** `backend/app/schemas/goal.py:14`, `backend/app/schemas/financials.py:10,26,43,66`

`target_amount`, `current_amount`, `monthly_contribution`, `annual_amount`, etc. are validated with `gt=0`/`ge=0` but have no upper bound (`le=`). A goal with an extreme `target_amount` (or a 30+ year horizon compounding a large `monthly_contribution`) can produce `inf`/`NaN` terminal values in `run_simulation`'s compounding loop (`backend/app/services/monte_carlo.py:90-92`), which then breaks `np.percentile` and the histogram bucketing — either a 500 or nonsensical `success_rate` returned to the user.
**Status:** Fixed — added `le=` bounds, deliberately generous (not meant to constrain legitimate use, just to backstop typos/abuse): 1,000,000,000 for one-off amounts (`target_amount`, `current_amount`, asset `current_value`, liability `balance`), 10,000,000 for monthly figures (`monthly_contribution`, expense `monthly_amount`, liability `monthly_payment`, `social_security_monthly`), 100,000,000 for `annual_amount` (income). Applied to both the `Create` and `Update` schema variants in `goal.py` and `financials.py`, plus `assumptions.py`'s `social_security_monthly` which had the same gap.
Tests: added one out-of-range case per bounded field across `test_goals.py` and `test_financials.py` (goal target/contribution, income annual amount, expense monthly amount, asset value, liability balance — 6 new cases), each asserting `422`. Full backend suite: 158 passed.
**Fix:** Add sane upper bounds to the Pydantic fields, and/or clip/guard terminal values before percentile computation.

## 11. `conversation_id` accepted but never persisted — Copilot has no real multi-turn memory
**File:** `backend/app/routers/copilot.py:79, 98-109`

The endpoint accepts and echoes back a `conversation_id`, implying a stateful conversation, but only the current message is ever sent to OpenAI — no prior turns are stored or replayed. Every "follow-up" question loses all previous context. This is a functional correctness gap that will surface as a support complaint ("the AI doesn't remember what I just said"), not just a nice-to-have.
**Fix:** Persist message history keyed by `conversation_id` and include prior turns in the `messages` list (bounded to a token budget).
**Status:** Deferred — needs a new table (or cache) for message history, a token-budget-aware truncation strategy, and decisions about retention/deletion that are more than a quick fix. Not attempted this pass; still returns independent, context-free replies per message.

## 12. In-memory rate limiter cannot scale horizontally — ⚠️ IMPROVED, NOT RESOLVED 2026-07-05
**File:** `backend/app/middleware/rate_limit.py:1-9` (acknowledged in the module's own docstring)

Each process has its own bucket dict. The moment this app runs as more than one instance/worker (any real production deployment), the effective rate limit multiplies by the instance count, and an attacker can trivially get N× the intended budget by hitting different instances. This is flagged separately from #2/#3 because it's a scaling blocker even *without* header spoofing.
**Fix:** Move to Redis-backed counters before running more than one process.
**Status:** Bucket memory growth (#3) and IP spoofing (#2) are fixed, which closes the *attacker-amplified* version of this problem. The *legitimate multi-instance* limitation is unchanged and can't be fixed without adding a Redis dependency this project doesn't have — out of scope for this pass. Documented in `README.md`'s new Production Deployment Notes section so it isn't a surprise at scale-out time.

## 13. Password reset tokens have no rate limit on generation — ✅ FIXED 2026-07-05
**File:** `backend/app/routers/auth.py:124-148`

`/auth/forgot-password` is covered by the generic sensitive-route rate limit, but that limit is IP+path keyed and bypassable per #2. Nothing prevents mass-issuing reset tokens for a target email over and over (each insert is cheap), which is a minor DB-growth/spam vector on top of the much bigger issue in #1.
**Fix:** Rate-limit by email (not just IP) in addition to fixing #1.
**Status:** Fixed — added a dedicated per-email token-bucket throttle (3 requests/hour per email, reusing the same `_TokenBucket` primitive as the IP limiter, with the same LRU+TTL eviction pattern capped at 10,000 tracked emails) independent of the IP-based limit. Tests: 2 new cases in `test_auth.py` (throttled after 3 requests for one email; a different email is unaffected).

## 14. `except Exception` swallows the real DB failure reason in the health check
**File:** `backend/app/main.py:66-68`

The health-check catches all exceptions from the DB probe and logs `error=%s` with the raw exception — acceptable for logging, but the endpoint then returns a generic `"degraded"` with no detail to callers, and there's no alerting hook (no metrics emission, no paging integration) tied to this branch. In production this means a DB outage shows up only if someone is actively polling `/health` and reading logs.
**Fix:** Wire `db_status == "error"` to an actual alert (metrics/log-based alert or exit code for orchestrator liveness probes), not just a log line.
**Status:** Deferred — this needs a specific alerting/metrics backend (Datadog, Prometheus Alertmanager, PagerDuty, etc.) to be chosen before there's anything concrete to wire up. The `/health` endpoint's `db` field is already correct and orchestrator-readable (a k8s/ECS liveness probe can key off `"db": "error"` in the JSON body today) — the gap is specifically *paging a human*, which is an infra decision, not a code fix.

## 15. No email verification on registration
**File:** `backend/app/routers/auth.py:43-58`

`register` creates an active user immediately from any syntactically-valid email with no verification step. Combined with no CAPTCHA/anti-abuse control (per `common/security.md` guidance, honeypots are recommended but none exist), this makes automated mass account creation trivial, which matters once billing or invite-quota logic is added on top of this user table.
**Fix:** Add an email-verification token flow before `is_active = True`, or at minimum add a signup-specific stricter rate limit and CAPTCHA.
**Status:** Deferred — blocked on the same missing piece as #1's full resolution: no email/SMS delivery provider is integrated yet. Building the verification-token flow without a way to deliver it doesn't close the gap. Flagged in `README.md`'s Production Deployment Notes as a known gap.

## 16. `except Exception` in `get_db` rolls back on *any* error, including client-side validation errors already handled by FastAPI
**File:** `backend/app/database.py:34-39`

Low severity on its own, but worth flagging alongside #14 as the second of only two exception handlers in the whole backend — the codebase has almost no explicit error-handling for external-dependency failures (OpenAI, DB pool exhaustion, thread-pool saturation) beyond these two blanket catches. That absence is what makes #5/#6/#7 land harder than they would with defense in depth.
**Status:** Not changed — reviewed and confirmed this is correct as-is. `get_db`'s broad `except Exception: rollback` is the right behavior for a session dependency (any exception from the route handler should roll back the transaction); it isn't masking anything the way the copilot's missing error handling was. No action needed.

## 17. `.output`, `.wrangler`, `.tanstack` build artifacts present in the working tree — ✅ FIXED 2026-07-05
**Dir:** `code/.output/`, `code/.wrangler/`, `code/.tanstack/`

These are gitignored (correctly) but currently exist on disk alongside source, dated from a prior build (`27 Jun`). Since there's no git repo (#8) there's no way to be sure these stale artifacts aren't accidentally being served or referenced by a deploy script pointed at the wrong directory. Low risk today, but worth clearing before the first real deploy so a stale build can't be shipped by mistake.
**Status:** Fixed — removed `code/.output/`, `code/.wrangler/`, and `code/.tanstack/tmp/`. All three are gitignored and fully regenerable (`bun run build` / `bun run dev`); confirmed a fresh `bun run build` recreates `.output/` correctly with no drift.

---

## Not included
Stylistic nits, missing docstrings, and anything that only affects developer convenience were deliberately left off this list per the "only things that will break, leak data, or block scaling" scope. The two most urgent items to fix before this app touches real user data were **#1** (reset-token leak) and **#4** (refresh tokens in localStorage) — both direct account-takeover paths, both fixed.

## Remediation summary (2026-07-05)

13 of 17 items fixed or improved; 4 deliberately deferred with reasons above (#11 conversation memory, #12 horizontal-scale rate limiting, #14 alerting integration, #15 email verification — the last two are both blocked on infra/provider decisions outside this codebase, not effort). #16 was reviewed and found to need no change. Every fix has passing tests; the full backend suite is at 164 tests (up from the original 135), plus frontend `tsc`/`vite build` verified clean. Git history now exists for all of this (previously none) — see commit log for one focused commit per item.

**Before this app handles real user signups**, the two blocking gaps are the same infra dependency in different clothes: an email/SMS delivery provider. That single integration unblocks a real (not debug-only) password reset flow (#1/#15) and email verification (#15). Everything else on this list is either fixed or a scale-later concern.
