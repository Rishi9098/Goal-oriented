# LIFE EVENT ENGINE — BACKEND HARDENING IMPLEMENTATION REPORT

**Role:** Principal Backend Engineer
**Scope:** The three remaining open findings from `LifeEventEngine_FinalReleaseAudit.md` that block a real release once the REST API layer exists (`LifeEventAPI_ImplementationReport.md`):

1. §4.2 (HIGH) — no idempotency protection on `record_life_event`
2. §1.3 (HIGH) — generic undo's conflict guard is field-scoped, not row-scoped
3. §4.3 (MEDIUM, treated as in-scope per this task's brief) — no row locking on read-then-write mutations

**Explicitly out of scope, and untouched:** all 17 event handlers, `RecommendationEngineV2`, `docs/backend.md`/`docs/architecture.md`/`CHANGELOG.md` (audit §5's documentation-trail finding), the "Death" product-completeness gap (§2.2), frontend of any kind. No existing router, schema, or handler signature changed in a breaking way — every extension is additive.

---

## 1. FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/alembic/versions/011_life_event_hardening.py` | New | Two additive, nullable columns: `life_events.idempotency_key` + its unique index, `life_event_effects.after_updated_at` |
| `backend/app/models/life_event.py` | Modified | `LifeEvent.idempotency_key` (nullable) + `UniqueConstraint(user_id, idempotency_key)`; `LifeEventEffect.after_updated_at` (nullable) |
| `backend/app/services/life_event_service.py` | Modified | `_get_by_idempotency_key`, `_row_updated_at`, `_updated_at_matches` (new, private); `record_life_event` gains an optional `idempotency_key` kwarg + flush-time race recovery; `undo_life_event`'s row loads use `with_for_update=True` and its conflict check is now state-or-timestamp |
| `backend/app/services/financials_service.py` | Modified | `adjust_asset_value`'s lookup gains `.with_for_update()` |
| `backend/app/schemas/life_event.py` | Modified | `LifeEventCreateRequest.idempotency_key` (new, optional field) |
| `backend/app/routers/life_events.py` | Modified | `create_life_event` forwards `idempotency_key`; the `audit_reference` lookup is now scoped to this life event's own id (was: "most recent for this user+action", silently wrong on a replay) |
| `backend/tests/test_life_event_hardening.py` | New (10 tests) | Idempotency (sequential + genuine flush-time race across two independent connections), the exact §1.3 cross-event undo scenario, and structural proof of the row locks |

**Not touched:** every one of the 17 event handler files, `RecommendationEngineV2`, `planning_service.py`, every other router. `record_life_event`'s new parameter is optional with a `None` default — every existing call site (17 handlers' own tests, the router) is unaffected without modification.

---

## 2. IDEMPOTENCY (§4.2)

**Problem:** `record_life_event` had no way to recognize a retried or double-submitted request. Combined with `adjust_asset_value`'s delta arithmetic, a duplicate `POST /life-events` for House Purchase, Home Sale, Business Sale, Major Medical Event, or Business Start would double-apply a real money delta, not just duplicate an audit row.

**Fix:**
- `LifeEvent.idempotency_key` — optional, client-supplied, `VARCHAR(100)`, with `UNIQUE(user_id, idempotency_key)`. `NULL` never collides with another `NULL` under standard SQL uniqueness (both SQLite and Postgres), so every caller that omits the key — which is every existing caller — is entirely unaffected.
- `record_life_event(..., idempotency_key: str | None = None)`: when given, checks `_get_by_idempotency_key` first; a match short-circuits and returns the *original* event untouched — the handler is never re-invoked, no new row of any kind is written.
- **Genuine concurrent duplicate** (two requests racing before either commits): the pre-check can miss on both, so both attempt to flush their own `LifeEvent` row. The loser's flush raises `IntegrityError` on the unique index; `record_life_event` catches it, rolls back (discarding everything it had written in that transaction, including whatever its own handler already flushed), and re-queries for the now-visible winner. This mirrors the exact recovery pattern already established in `routers/assumptions.py`'s `get_assumptions` for an analogous first-access race — not a new idiom for this codebase.
- The router's `audit_reference` lookup was quietly wrong for the replay case before this task (it picked "most recent `life_event_recorded` AuditLog row for this user", which is correct only if no other event was recorded in between). Fixed to filter by `AuditLog.after_state["life_event_id"]` matching this specific event's id, via SQLAlchemy JSON-path indexing — verified directly against SQLite.

**Tests** (`test_life_event_hardening.py::TestIdempotencySequential`, `TestIdempotencyRouter`, `TestIdempotencyRace`):
- Duplicate key at the service layer returns the same event, replays the *original* inputs, and only one `Goal` exists afterward.
- Two different keys record two independent events (the key doesn't cause blanket dedup).
- Omitting the key entirely still records independent events (backward compatibility for every pre-existing caller).
- Duplicate `POST /life-events` with the same key at the HTTP layer returns identical `life_event.id` and `audit_reference` in both responses, with only one `Asset` created.
- The genuine flush-time race: two independent sessions on a dedicated temp-file SQLite database (see §4 below for why), one committing first, the second forced through the `IntegrityError` recovery path — asserts it returns the winner's id and that exactly one `Goal`/`LifeEvent` row exists across both connections afterward.

---

## 3. UNDO CONFLICT DETECTION — ROW-LEVEL FINGERPRINT (§1.3)

**Problem:** `undo_life_event`'s only conflict check compared the row's *current* values against `after_state` — but `after_state` only ever contains the specific fields that one effect touched. If event A updates `target_amount` and a later, unrelated event B updates `name` on the *same* Goal row, undoing A finds `target_amount` still matches A's own `after_state` and reports "no conflict" — even though the row is demonstrably not in the state A left it in. Silently applying A's stale-partial undo in that state is exactly the audit's concern.

**Fix:** Every one of the nine entity tables this engine touches already bumps `updated_at` via `onupdate=func.now()` on *any* column change (verified directly against every model file). `LifeEventEffect.after_updated_at` now captures that timestamp at record time, read via a direct Core column `select()` (not an ORM attribute read — see §5 for why that distinction mattered). `undo_life_event`'s conflict check is now `state_changed OR timestamp_changed`: the pre-existing field-scoped check stays exactly as it was (still catches the case `after_updated_at` can't, e.g. two effects racing without a row change in between on some hypothetical backend without `updated_at`), and the new row-level fingerprint catches everything it couldn't.

**Test** (`test_life_event_hardening.py::TestUndoRowFingerprint`): reproduces the audit's own scenario directly — one handler updates only `target_amount`, a second, later, unrelated handler updates only `name` on the same Goal. Asserts `event_a.effects[0].after_state` never mentions `name` (proving the pre-hardening check would have missed this), then asserts `undo_life_event(event_a)` is now blocked with reason `"Row has changed since this event was recorded"`. A companion negative-control test confirms a truly untouched row still undoes cleanly — the new fingerprint doesn't over-block.

---

## 4. CONCURRENCY PROTECTION (§4.3)

**Problem:** `adjust_asset_value` (the one genuinely delta-based read-modify-write in this codebase — every other mutation function does an absolute-value `SET`, not a `+=`) read `current_value`, computed a new value in Python, and wrote it back with no row lock. Two concurrent callers reading the same starting value would silently lose one delta. `undo_life_event`'s per-row load had the same gap between its conflict check and its reversal write.

**Fix:** `.with_for_update()` added to `adjust_asset_value`'s `SELECT`; `undo_life_event`'s `db.get(model_cls, effect.entity_id, with_for_update=True)`. Both are real row locks under Postgres (production) and are silently ignored by SQLite (this test suite's backend, which has no row-level locking) — this asymmetry is inherent to the two backends, not a gap in this fix.

**Why the tests are structural, not a live race:** this project's test fixture (`tests/conftest.py`) binds every session in a test to a single `StaticPool` connection — verified directly (two sessions opened from the fixture's engine, even held open concurrently, return the exact same physical connection). There is no way to construct two independently-committing transactions on it, so a real "both read the stale value, second write clobbers the first" reproduction isn't buildable on this harness without standing up Postgres, which is outside this task's stated scope. Rather than skip the finding or fake a race that wouldn't actually prove anything, `TestConcurrencyProtection` proves the mitigation the honest way available:
- Inspects the actual SQLAlchemy Core construct (`Select._for_update_arg`) via a `before_execute` engine event, for both `adjust_asset_value`'s lookup and `undo_life_event`'s row load — confirmed present in both. This is deliberately *not* a check against rendered SQL text: SQLite's own compiler silently drops the `FOR UPDATE` clause at render time (confirmed separately, with a throwaway script against a real `aiosqlite` engine — the query executes without error and without emitting the clause), so a text-based assertion would report a false negative on the very backend this suite runs against, while the lock genuinely is requested at the ORM/Core layer and does take effect on Postgres.
- A sequential-correctness test confirms the arithmetic the lock protects is itself right (three sequential deltas on the same asset land on the correct final total) — proof the lock is guarding a real, correct critical section rather than papering over broken math.

This is disclosed here plainly rather than glossed over: automated proof of the actual concurrent-corruption scenario requires a multi-connection backend this test environment doesn't have.

---

## 5. A REGRESSION SURFACED AND FIXED DURING THIS WORK

The first version of `_row_updated_at` read the touched row's `updated_at` via `db.get(...)` followed by a plain `getattr`. This passed lint and type-checking but failed at runtime for any handler that flushes a write and does **not** immediately `db.refresh()` the row afterward (`close_liability`, used by Loan Payoff, Home Sale, and Business Sale, is exactly this shape) — SQLAlchemy always expires an `onupdate=func.now()` column after a flush, since only the database knows the value it actually computed, and a bare `getattr` on that expired attribute triggers an implicit, un-awaited lazy-reload that raises `MissingGreenlet` under the async driver. This surfaced as 12 failing tests across `test_life_event_service.py`, `test_home_sale_handler.py`, and `test_business_sale_handler.py` during this task's own verification pass.

**Fix:** `_row_updated_at` now issues a direct Core `select()` of just the `updated_at` column, bypassing ORM attribute state entirely — reading the true just-committed value regardless of any handler's own refresh discipline, and requiring no change to any of the 17 handlers to stay correct.

---

## 6. TEST RESULTS

```
ruff check app/                    → All checks passed!
mypy --strict app/                 → Success: no issues found in 87 source files
pytest -q --no-cov (full suite)    → 673 passed (663 pre-existing + 10 new), 0 failed
```

Every pre-existing test (all 17 handlers, the router, the generic engine, every other domain) passes unmodified — this task's changes are additive at both the schema and the service-function-signature level.

---

## 7. WHAT REMAINS OPEN (explicitly not addressed here, per this task's own scope)

- §5's documentation-trail finding (`CHANGELOG.md`, `docs/backend.md`, `docs/architecture.md` have no mention of the 17 events) — untouched.
- §2.2's product-completeness gap ("Death" has no corresponding life event) — untouched.
- A genuine multi-connection concurrency test against a real Postgres backend — not buildable on this project's current SQLite-only test harness; flagged above rather than worked around.
- Frontend of any kind — not built, per this task's explicit instruction.

**Stop here**, per this task's own brief.
