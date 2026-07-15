# LIFE EVENT ENGINE — REST API LAYER IMPLEMENTATION REPORT

**Role:** Principal Backend Engineer
**Scope:** `LifeEventEngine_FinalReleaseAudit.md`'s single release-blocking finding — *"The Life Event Engine has no API surface."* This task addresses only that finding: a new router exposing the five endpoints `LifeEventEngineArchitecture.md` §10 specified, built entirely on top of the existing, unmodified `life_event_service.py` and all 17 event handlers. **No engine redesign, no handler changes, no frontend.**

---

## 1. FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/schemas/life_event.py` | New | Request/response Pydantic models — no ORM model is ever returned directly |
| `backend/app/routers/life_events.py` | New | The five endpoints; all business logic delegated to `life_event_service` |
| `backend/app/services/life_event_service.py` | Modified (additive only) | One new function, `list_life_events_paginated` — the existing `list_life_events` is untouched, byte-for-byte, and its own 22 Phase A tests still pass unchanged |
| `backend/app/main.py` | Modified | Registers `life_events.router` — two lines (import + `include_router`) |
| `backend/tests/test_life_events_router.py` | New (27 tests) | Full endpoint coverage: creation, listing/pagination/filters, get-by-id, undo (success/conflict/force/already-undone), preview, ownership, unsupported events, invalid payloads |

**Not touched:** all 17 event handlers, `life_event_service.py`'s `record_life_event`/`preview_life_event`/`undo_life_event`/`get_life_event`/`list_life_events`/the generic undo framework, `RecommendationEngineV2`, `FinancialContext`/`planning_service.py`, and every other router. Confirmed by re-reading each file before and after, and by the full 636 pre-existing tests passing with zero modification.

---

## 2. ENDPOINTS ADDED

All under `POST /api/v1/life-events*` / `GET /api/v1/life-events*`, matching `LifeEventEngineArchitecture.md` §10 exactly, with one addition (`GET /{id}`) this task's own brief requested beyond the original design.

| Method | Path | Calls | Status codes |
|---|---|---|---|
| `POST` | `/life-events` | `record_life_event` | 201 created, 401/403 unauthenticated, 404 handler-owned ownership/not-found, 422 unsupported event or invalid payload |
| `GET` | `/life-events` | `list_life_events_paginated` (new) | 200, 401/403 |
| `GET` | `/life-events/{id}` | `get_life_event` | 200, 401/403, 404 (not found *or* not owned — never distinguishable) |
| `POST` | `/life-events/{id}/undo` | `undo_life_event` | 200 success, 409 conflict (blocked, with the conflict list), 422 already-undone, 401/403, 404 |
| `POST` | `/life-events/preview` | `preview_life_event` | 200 (including a handler-caught validation failure — see §4), 401/403, 422 unsupported event |

Every endpoint's handler body is three steps only: validate the request shape/event-type, call the one relevant `life_event_service` function, translate the result into a response model. No endpoint contains an `if`/`for` that decides *what a life event does* — that remains entirely inside the 17 handlers, untouched.

---

## 3. SCHEMAS ADDED (`app/schemas/life_event.py`)

| Schema | Purpose |
|---|---|
| `LifeEventCreateRequest` | `event_type`, `occurred_on`, `inputs` (free-form JSON — see §4 for why), `notes` |
| `LifeEventPreviewRequest` | `event_type`, `inputs` |
| `UndoRequest` | `force: bool = False` |
| `EntityEffectResponse` | Mirrors `EntityEffect`/`LifeEventEffect` — `entity_table`, `entity_id`, `change_type`, `before_state`, `after_state` |
| `LifeEventResponse` | Mirrors `LifeEvent` + its effects + a derived `audit_action` field (see §4) — built field-by-field by the router, never `LifeEvent.__dict__` or a `from_attributes` pass-through of the ORM row |
| `LifeEventCreateResponse` | `{ life_event, audit_reference }` |
| `LifeEventListResponse` | `{ items, total, limit, offset }` |
| `LifeEventPreviewResponse` | `{ event_type, effects, affected_entities, validation_errors }` |
| `UndoConflictResponse` / `UndoResponse` | Mirror `UndoConflict`/`UndoResult` exactly |

**No internal ORM model is ever exposed.** `_to_life_event_response`/`_to_effect_response` in the router build every response field-by-field from the ORM row/dataclass; `response_model=` on every route is one of the schemas above, never `LifeEvent`/`LifeEventEffect` itself.

---

## 4. VALIDATION RULES (and the two deliberate design decisions behind them)

### 4.1 `inputs`/`payload` stays a free-form JSON object, not 17 typed sub-schemas

Each of the 17 handlers already documents and enforces its own required/optional fields (this was the entire subject of the 17 `LifeEvent_<Event>_ImplementationReport.md` files). Building 17 separate Pydantic request schemas here would either duplicate that documentation in a second place (drifting the moment a handler's own inputs change) or require modifying handlers to accept typed objects instead of `dict[str, Any]` — both explicitly out of scope ("Do NOT redesign the engine," "Do NOT modify event handlers"). `inputs` is validated exactly as deep as the handler itself already validates it — no shallower, no deeper.

### 4.2 Router-level exception translation, not new validation logic

Handlers raise three kinds of errors today: a handler-owned `HTTPException` (e.g. a referenced entity not found — already correctly shaped, passed through untouched), a `KeyError`/`TypeError` (a required `inputs` key missing or the wrong shape), or a `ValueError` (e.g. family validation, or the engine's own "unknown event type"/"already undone"). `create_life_event` and `undo_life_event` catch the latter two categories and translate them to `422`, so a malformed request produces a clean API error instead of an unhandled `500` — this is exception *translation*, not new business rules; the underlying decision of "is this input valid" is still made entirely inside the handler/engine.

### 4.3 `POST /preview` never raises for a handler-caught validation problem

This is the one place validation strategy differs, deliberately: a dry run's entire purpose is to show the user what's wrong *before* committing, so a `KeyError`/`ValueError`/`TypeError` from the handler is captured into `validation_errors` and returned as a normal `200`, with `effects=[]`. An **unsupported `event_type`** is treated differently (`422`) on both `preview` and `create` — that is a structural/routing problem ("this isn't a real event"), not a payload-shape problem a dry run is meant to surface gracefully.

### 4.4 `audit_action` is derived, not queried (avoiding an N+1)

`LifeEventEngine_FinalReleaseAudit.md` specifically praised the engine's notification/recommendation fan-out for having no N+1, and flagged it as something not to regress. `record_life_event`/`undo_life_event` always write an `AuditLog` row with `action="life_event_recorded"`/`"life_event_undone"` matching the resulting `status` exactly — so `LifeEventResponse.audit_action` is computed from the already-loaded `life_event.status` with zero extra query, for every item on the list endpoint. The one place a *real* audit reference is genuinely queried is `POST /life-events`'s `audit_reference` (the actual `AuditLog.id` just written) — a single, one-time lookup on creation, not a per-item cost on any list.

---

## 5. SECURITY VERIFICATION

| Requirement | How it's satisfied | Evidence |
|---|---|---|
| Authenticated user | Every endpoint depends on `get_current_user` (existing dependency, unchanged) | `test_requires_authentication` × 5, all assert `403` (this app's `HTTPBearer(auto_error=True)` default for missing credentials — confirmed against existing router conventions, not a new behavior) |
| Ownership | `current_user` (JWT-derived) is passed to every service call; never a client-supplied `user_id` anywhere in a request schema | Grepped `app/schemas/life_event.py` — no `user_id` field exists in any request model |
| Cross-user access (IDOR) | `get_life_event`/`undo_life_event` already filter by `user_id` at the data layer (unchanged, pre-existing engine behavior) — a non-owned id 404s exactly like a nonexistent one, never a distinguishable 403 that would leak existence | `test_another_users_event_returns_404_not_403` on both `GET /{id}` and `POST /{id}/undo` |
| Unsupported event types | Checked against `life_event_service.registered_event_types()` before calling the engine, on both `create` and `preview` | `test_unsupported_event_type_returns_422` × 2 |
| Invalid payloads | Translated to `422` (create) or `200` + `validation_errors` (preview, by design — §4.3) | `test_invalid_payload_missing_required_field_returns_422`, `test_invalid_payload_returns_200_with_validation_errors_not_an_http_error` |

**Explicitly not addressed here, per the task's own STOP list** (unchanged from `LifeEventEngine_FinalReleaseAudit.md`'s findings, now simply re-confirmed still present): no idempotency key (a duplicate `POST /life-events` still creates two life events; a delta-based handler like `adjust_asset_value` would still double-count), no row-level locking on any read-then-write mutation. Both remain real, known gaps — not fixed, not hidden, exactly as instructed.

---

## 6. TESTS ADDED

`tests/test_life_events_router.py` — 27 tests, against the real engine and real handlers (Bonus, House Purchase, Education Planning — no mocking):

| Category | Tests |
|---|---|
| `POST /life-events` | Records a real event (Bonus) and returns life event + effects + a genuinely distinct `audit_reference`; requires auth; unsupported event → 422; missing required field → 422; a handler-owned 404 (bad down-payment asset id on House Purchase) passes through unchanged |
| `GET /life-events` | Newest-first ordering (with the same SQLite-timestamp-resolution workaround `test_life_event_service.py`'s own ordering test already established); `limit`/`offset`; `event_type` filter; `start_date`/`end_date` filter; only returns the authenticated user's own events; requires auth |
| `GET /life-events/{id}` | Returns the event with effects + `audit_action`; 404 for a nonexistent id; 404 (not 403) for another user's event; requires auth |
| `POST /life-events/{id}/undo` | Clean undo → 200; a since-changed row → 409 with the conflict listed; `force=true` overrides the conflict; undoing an already-undone event → 422; nonexistent event → 404; another user's event → 404; requires auth |
| `POST /life-events/preview` | Returns predicted effects with nothing written; a preview never leaks into the real history (`GET /life-events` still shows only the real event); unsupported event → 422; invalid payload → 200 with `validation_errors`, not an HTTP error; requires auth |

**Result:** 27/27 pass. Full backend suite: **663 passed** (636 pre-existing + 27 new), zero modified, zero skipped.

Two things worth recording precisely because they weren't obvious going in:

- **This app's `HTTPBearer` default returns `403`, not `401`, for a missing Authorization header.** My first draft of every `test_requires_authentication` asserted `401`; all five failed until corrected to `403`, matching the auth dependency's actual, pre-existing, unchanged behavior — not something this task's router changed.
- **The test client's `get_db()` override does not replicate the real dependency's rollback-on-exception behavior** (`conftest.py`'s `override_get_db` just `yield`s the shared session with no `try`/`except`/`rollback`). A test asserting "a failed compound event via HTTP leaves nothing durable" would only be testing an artifact of the test harness, not the router — atomicity itself is already exhaustively proven per-handler (e.g. `test_house_purchase_handler.py::TestRollback`) against the real `get_db()` path. That test was removed in favor of a code-level statement (verified by inspection): the router calls zero `db.commit()`/`db.rollback()` of its own.

---

## 7. BACKWARD COMPATIBILITY

- **Full suite: 663 passed**, zero skipped, zero regressions.
- **`test_life_event_service.py`** (22 tests, Phase A's own suite): unchanged, all pass — `list_life_events` was not touched; `list_life_events_paginated` is a wholly new, additive function.
- **Every one of the 17 event-handler test suites**: unchanged, all pass — no handler file was modified.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 87 source files (85 pre-existing + `schemas/life_event.py` + `routers/life_events.py`).
- No existing endpoint's request/response schema, status code, or URL changed. `main.py`'s only change is the two lines needed to mount the new router.

---

## 8. PERFORMANCE IMPACT

- **List endpoint: two queries, not N+1.** `list_life_events_paginated` issues one `COUNT` query (for `total`) and one page query with `selectinload(LifeEvent.effects)` (the same eager-load `get_life_event` already uses) — one query for the page of events, one for all their effects combined, regardless of page size. Confirmed by reading the query shape directly; no per-item follow-up query exists anywhere in the router.
- **`audit_action` costs zero queries** — derived from the already-loaded `status` field (§4.4), specifically to avoid the N+1 a naive "look up the AuditLog row for each list item" approach would have introduced.
- **`POST /life-events`'s `audit_reference` costs exactly one extra query**, once, on creation only — not incurred by any read endpoint.
- **No new index required.** The paginated query filters on `user_id` (indexed), `event_type` (indexed), and `occurred_on` (not indexed) — a date-range filter on `occurred_on` will table-scan a user's own life events, which is bounded by how many events one user can plausibly have (not a cross-user scan); acceptable at the scale this feature will see for the foreseeable future, and consistent with the project's existing indexing choices (e.g., `Expense.category`/`Asset.asset_type` are similarly unindexed free-text fields elsewhere).

---

## 9. REMAINING RELEASE BLOCKERS

This task closed exactly one finding from `LifeEventEngine_FinalReleaseAudit.md` — the missing API surface — and nothing else. Every other finding from that audit is **unchanged and still open**, per this task's own explicit STOP instructions:

1. **No idempotency protection** (`LifeEventEngine_FinalReleaseAudit.md` §4.2) — a duplicate `POST /life-events` submission still creates two life events; for a delta-based handler (`adjust_asset_value`, used by House Purchase's down payment, Home Sale/Business Sale's proceeds, Major Medical Event's lump sum, Business Start's funding), this still double-counts real money. **Explicitly not fixed here** ("Do NOT fix idempotency").
2. **No row-level locking** (§4.3) — the read-then-write pattern in `adjust_asset_value` and elsewhere remains a latent race condition under true concurrency. **Explicitly not fixed here** ("Do NOT add row locking").
3. **The field-scoped (not row-scoped) undo conflict guard** (§1.3) — undoing an older event after a newer, unrelated event touched a different field on the same row can still silently apply a stale partial write. Unchanged; this router adds no new undo logic of its own (by design — "Do NOT create event-specific undo logic").
4. **No frontend** — this task built only the API layer; `code/src` still has zero Life Event references. A UI is still the entire remaining scope of Milestone 2 from a product standpoint.
5. **No `CHANGELOG.md`/`docs/backend.md`/`docs/architecture.md` entries** for the Life Event Engine or this new router — the same documentation-debt finding from the prior audit, now also true of this new API surface, since this task's own scope was the API layer only.
6. **`RecommendationEngineV2` was not touched** here, per instruction, and did not need to be — it already reacts live to every write a life event performs, exactly as verified in the prior audit.

**With this task's work included, the release-blocking finding that produced a NO GO decision — "no API surface exists" — is resolved.** The remaining blockers above (idempotency, row locking, the undo guard gap, and the frontend) were always understood to be separate, explicitly out-of-scope work for this task and should each be scoped as their own follow-up.
