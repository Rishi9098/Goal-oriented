# LIFE EVENT ENGINE — PHASE A (FOUNDATION) IMPLEMENTATION REPORT

**Role:** Principal Backend Engineer
**Scope:** `LifeEventEngineArchitecture.md` §3/§4/§7's foundation only — the two tables, the SQLAlchemy models, the Alembic migration, the generic orchestration/undo service, and its audit/transaction integration. **Zero concrete life events were implemented.** `_HANDLERS` ships empty; the engine has nothing registered to record until a later phase defines a real event type (salary raise, marriage, etc.).

---

## FILES CHANGED

| File | Status | Lines |
|---|---|---|
| `backend/app/models/life_event.py` | New | 109 |
| `backend/app/models/__init__.py` | Modified (2 lines: import + `__all__` entry) | — |
| `backend/alembic/versions/010_life_events.py` | New | 72 |
| `backend/app/services/life_event_service.py` | New | 389 |
| `backend/tests/test_life_event_service.py` | New | 559 |

No router, no Pydantic schema, and no frontend file was touched. A router that can only ever 422 on every `event_type` (since none is registered) would be unused surface area — deferred to whichever phase first defines a real event, consistent with "Do NOT implement any specific life events."

`RecommendationEngineV2` (`family_recommendations_service.py`), `FinancialContext`/`get_financial_context` (`planning_service.py`), `routers/dashboard.py`, and `routers/reports.py` were **not modified** — confirmed by `git status`, and by their unchanged coverage/behavior in the validation run below.

---

## DATABASE CHANGES

Migration `010_life_events.py` (chained on `009`, matching this project's existing raw-SQL `op.execute(...)` style rather than Alembic's `op.create_table()` DSL, per migration `009`'s own precedent):

```sql
CREATE TABLE life_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type    VARCHAR(50) NOT NULL,
    occurred_on   DATE NOT NULL,
    recorded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    inputs        JSON NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'applied',
    undone_at     TIMESTAMPTZ,
    notes         TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);
-- + indexes on user_id, event_type

CREATE TABLE life_event_effects (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    life_event_id  UUID NOT NULL REFERENCES life_events(id) ON DELETE CASCADE,
    entity_table   VARCHAR(50) NOT NULL,
    entity_id      UUID NOT NULL,
    change_type    VARCHAR(20) NOT NULL,
    before_state   JSON,
    after_state    JSON,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- + indexes on life_event_id, entity_id
```

`event_type` is a plain `VARCHAR`, not a DB enum — adding a real event type in a later phase is application code only, never a migration (matching `income_sources.source_type`/`expenses.category`'s existing convention, deliberately not `goals.category`'s DB-enum convention). `entity_table`/`entity_id` on `life_event_effects` are **not** a polymorphic foreign key — a single life event can touch rows across nine different tables (per `LifeEventEngineArchitecture.md` §3's list), and a real FK per possible target table isn't worth the complexity for what is fundamentally an audit/undo pointer, not a relationship the ORM needs to traverse.

**Migration verified against the live Postgres instance, both directions:**
```
$ alembic upgrade head    # 009 -> 010, succeeded
$ psql ... \d life_events \d life_event_effects   # both tables, all columns/indexes/FKs confirmed exactly as designed
$ alembic downgrade 009   # 010 -> 009, succeeded, tables dropped
$ alembic upgrade head    # re-applied cleanly, left at 010 (head)
```

---

## SERVICE LAYER

`app/services/life_event_service.py`, structurally parallel to `family_recommendations_service.py` (depends on existing entity models, adds no calculation of its own):

**Generic entity registry** (`_ENTITY_MODELS`) — a table-name → ORM-class lookup for undo, covering exactly the nine tables `LifeEventEngineArchitecture.md` §3 names (`income_sources`, `expenses`, `assets`, `liabilities`, `goals`, `household_members`, `dependents`, `user_profiles`, `financial_assumptions`). Encodes no business rule about *when* any table is written — purely mechanical.

**Generic orchestration interface** (item 6): `LifeEventHandler` is a `Protocol` with one method, `apply(db, user, inputs) -> list[EntityEffect]`. `register_handler`/`unregister_handler`/`registered_event_types` manage a module-level `_HANDLERS` dict — empty in this phase. `record_life_event` and `preview_life_event` both call `_require_handler(event_type)`, which raises `ValueError` for any `event_type` not yet registered (the correct, expected behavior in Phase A, since none is).

**Generic undo framework** (item 7): `undo_life_event` reverses every `LifeEventEffect` of a life event, in reverse order, using only `entity_table`/`entity_id`/`before_state`/`after_state` — no event-specific branch anywhere in the function. Guarded: an effect is only reversed if the live row still matches the `after_state` captured at record time (compared via a generic, schema-metadata-driven `snapshot()`/`_restore_value()` pair — JSON-safe serialization keyed off each column's own declared Python type, not a per-field special case), unless `force=True` is passed, in which case a state-mismatch conflict is overridden (but a genuinely missing row or an unrecognized `entity_table` remains unresolvable regardless of `force` — those aren't state disagreements, they're rows the engine cannot act on at all).

**Audit integration** (item 8): `record_life_event` writes one `AuditLog` row (`action="life_event_recorded"`, `after_state` pointing at the new `life_event_id`); `undo_life_event` writes a matching `action="life_event_undone"` row. This is a lightweight courtesy pointer into the existing generic ledger, not a competing audit system — `life_events`/`life_event_effects` remain the authoritative record.

**Request-scoped transaction support** (item 9): every function calls `db.flush()` where a generated id is needed and **never** `db.commit()` — verified by direct inspection (no `commit()` call anywhere in the file) and by `test_never_commits_a_handler_failure_partway_through`, which proves a mid-event failure leaves nothing durable once the caller rolls back. This is the exact discipline `TransactionConsistencyImplementationPlan.md` established for `goals.py`/`family_service.py`, now extended to this new module from day one rather than retrofitted later.

**`preview_life_event`** runs a handler inside a SAVEPOINT (`db.begin_nested()`) that is always rolled back on exit — the effects a caller sees in preview are produced by the exact same code `record_life_event` would run, and nothing else pending on the caller's session is disturbed (verified by `test_preview_does_not_disturb_other_pending_work_on_the_session`).

---

## TESTS ADDED

`tests/test_life_event_service.py` — 22 tests, all against the real service (no mocking), using two test-only scaffolding handlers (`_CreateGoalHandler`, `_UpdateGoalHandler`, `_FailingHandler`) registered/unregistered per-test via an autouse fixture that diffs the handler registry before/after so nothing leaks between tests. **No concrete life event is implemented or asserted anywhere in this file** — these handlers exist only to exercise the generic engine.

| Area | Tests |
|---|---|
| Orchestration interface | Phase A ships with zero registered types; register/list; unknown `event_type` raises on both `record` and `preview` |
| Record | Effect + event correctly persisted and readable; generic `AuditLog` row written; **a handler failure partway through leaves nothing committed once the caller rolls back** (the core proof this phase exists to deliver, directly exercising the Transaction Consistency refactor) |
| Preview | Returns effects but persists nothing; does not disturb other pending work on the same session (SAVEPOINT scoping) |
| Read | Ownership isolation between users; most-recent-first ordering |
| Undo | Reverses a create-effect via soft-delete; reverses an update-effect via `before_state` restoration (including a `date`-typed field's round trip through the generic serializer); writes a matching `AuditLog` row; blocks on a state conflict and leaves everything untouched; `force=True` overrides a state conflict; blocked when the row no longer exists at all; blocked for an unrecognized `entity_table`; rejects undoing an already-undone event; rejects undoing another user's event; rejects a nonexistent event id |
| Schema shape | Deleting a `LifeEvent` cascades its `LifeEventEffect` rows |

**Result:** 22/22 pass. `life_event_service.py` itself: 94% coverage (145 statements, 9 uncovered — the uncovered lines are the UUID-conversion branch of the generic serializer and the "skip an entirely unresolvable forced-undo effect" branch, neither exercised because Phase A's own test handlers only ever touch `str`/`float`/`date`-typed `Goal` fields; in line with this codebase's other services, which typically carry a handful of uncovered defensive lines too — `family_service.py` 97%, `notification_service.py` 96%, `scheme_eligibility_service.py` 98%).

---

## BACKWARD COMPATIBILITY

- **Full suite: 404 passed** (382 pre-existing + 22 new), zero modified, zero skipped.
- **RecommendationEngineV2** (`test_family_recommendations.py`, all 38 tests including the 4 explicit change-triggers-recommendation tests): unaffected — not imported by, and does not import, `life_event_service.py`.
- **Dashboard / Reports** (`test_dashboard.py`, `test_reports.py`, `test_family_dashboard.py`): unaffected — `planning_service.py` was not touched.
- **Financial CRUD** (`test_financials.py`): unaffected.
- **Family** (`test_family_router.py`, `test_family_insurance.py`, `test_family_schemes.py`): unaffected.
- **`ruff check app/`**: all checks passed. **`mypy app/` (strict)**: no issues found in 66 source files (65 pre-existing + `life_event.py` + `life_event_service.py`).
- No existing table, column, endpoint, or response shape changed. `app/models/__init__.py`'s only change is two additive lines (import + `__all__` entry) — every existing entry is untouched.

---

## PERFORMANCE IMPACT

- Two new tables, both indexed on their foreign keys (`user_id`, `event_type` on `life_events`; `life_event_id`, `entity_id` on `life_event_effects`) — no query against any existing table changes shape, and nothing in this phase is read from anywhere existing (Dashboard, Reports, Recommendations, Notifications all remain exactly as fast as before, since none of them queries these new tables).
- `record_life_event`/`undo_life_event` each issue a small, fixed number of statements proportional to the number of effects a (future) handler produces — no N+1 pattern, confirmed by the shape of the code itself (a single loop over an already-in-memory `effects` list, one `INSERT`/`UPDATE` per effect).
- `undo_life_event`'s conflict check issues one `db.get()` (a primary-key lookup, the cheapest possible query) per effect — bounded by however many entities one life event touches (at most a handful, per the architecture's own catalog), not a table scan.

---

## READY FOR PHASE B?

**Yes.** The engine's generic surface (`register_handler`, `record_life_event`, `preview_life_event`, `undo_life_event`, `list_life_events`, `get_life_event`, `snapshot`) is complete, tested, and exercised end-to-end by scaffolding handlers standing in for a real one. A future concrete event (e.g. Loan Payoff, per the architecture's own recommended Phase B starting point — one entity, one effect, the simplest case) needs only to:
1. Implement `LifeEventHandler.apply()` by calling the *existing* entity-mutation logic (exactly as `routers/financials.py`'s liability soft-delete already does), building its `EntityEffect`s via `life_event_service.snapshot()`.
2. Call `life_event_service.register_handler("loan_payoff", handler)` once, at import/startup time.

No further foundation work is required before that can happen. Not yet built, correctly deferred: any HTTP surface (`POST /life-events`, etc.) and Pydantic request/response schemas — both depend on knowing what a real event's `inputs` shape looks like, which only exists once Phase B defines its first concrete event.

**Stopping here, as instructed.** No specific life event was implemented in this phase.
