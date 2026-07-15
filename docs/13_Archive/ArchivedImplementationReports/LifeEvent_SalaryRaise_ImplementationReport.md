# LIFE EVENT ENGINE — SALARY RAISE IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #1 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.1's Salary Raise — an `IncomeSource.annual_amount` update, with an optional linked step that also bumps a `Goal.monthly_contribution` (routing through ADR-001's existing conditional Monte Carlo trigger). **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/notification_service.py` | Modified (cross-cutting, benefits every subsequent event) | Added `_collect_life_event_facts` — the generic Life Event notification collector the Phase B.1 report described but never built; added `"life_event"` handling driven by a per-`event_type` `_LIFE_EVENT_COPY` dict |
| `backend/app/schemas/notification.py` | Modified | Added `"life_event"` to `NotificationSource` |
| `backend/app/services/planning_service.py` | Modified (cross-cutting) | Extracted `update_goal_fields()` — the exact ADR-001-conditional mutation `PATCH /goals/{id}` already performed, now the one implementation both the router and Salary Raise's optional goal step call |
| `backend/app/routers/goals.py` | Modified | `update_goal` now calls `planning_service.update_goal_fields()` instead of repeating the inline query/setattr/conditional-recalc logic |
| `backend/app/services/financials_service.py` | Modified | `update_income_source()`'s return type changed from `IncomeSource` to `tuple[IncomeSource, dict, dict]` — a before/after snapshot, mirroring `close_liability`'s established shape, for a caller building a `LifeEventEffect` |
| `backend/app/routers/financials.py` | Modified | `update_income` unpacks the new 3-tuple; behavior unchanged |
| `backend/app/services/salary_raise_handler.py` | New (69 lines) | `SalaryRaiseHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `SalaryRaiseHandler` against the engine at app-creation time |
| `backend/tests/test_notifications.py` | Modified | Added `test_life_event_appears_as_notification` |
| `backend/tests/test_salary_raise_handler.py` | New (17 tests) | The full Salary Raise test suite |

**Not touched:** `family_recommendations_service.py`'s rule logic, `monte_carlo.py`, `routers/dashboard.py`, `routers/reports.py` — confirmed by every one of their existing tests passing unchanged.

---

## HANDLER DESIGN

```python
class SalaryRaiseHandler:
    async def apply(self, db, user, inputs):
        income_id = uuid.UUID(inputs["income_source_id"])
        new_annual_amount = float(inputs["new_annual_amount"])

        income, before_state, after_state = await financials_service.update_income_source(
            db, user, income_id, IncomeSourceUpdate(annual_amount=new_annual_amount)
        )
        effects = [EntityEffect(
            entity_table="income_sources", entity_id=income.id, change_type="update",
            before_state=before_state, after_state=after_state,
        )]

        goal_id = inputs.get("goal_id")
        new_monthly_contribution = inputs.get("new_monthly_contribution")
        if goal_id is not None and new_monthly_contribution is not None:
            goal, goal_before, goal_after = await planning_service.update_goal_fields(
                db, user, uuid.UUID(goal_id),
                {"monthly_contribution": float(new_monthly_contribution)},
            )
            effects.append(EntityEffect(
                entity_table="goals", entity_id=goal.id, change_type="update",
                before_state=goal_before, after_state=goal_after,
            ))
        return effects
```

69 lines including the module docstring, imports, and the class's own docstring. It computes nothing: both writes go through functions the corresponding `PATCH` endpoints already call.

1. **Validate the income source (and, if linked, the goal) exist and are owned by the caller** — `update_income_source`/`update_goal_fields` each raise their own `HTTPException(404)`, identical to what their respective routers already raised. No second check.
2. **Optional linked step, explicit opt-in only** — the goal step fires only when *both* `goal_id` and `new_monthly_contribution` are present in `inputs`. A `goal_id` with no accompanying contribution figure is a no-op for the goal (tested explicitly — `test_apply_ignores_goal_id_when_new_monthly_contribution_is_absent`), matching the architecture's "never assume an optional step" rule.
3. **Record Life Event / Effects** — generic, from Phase A, unchanged. The handler returns one effect (income-only path) or two (income + goal path), in write order.
4. **ADR-001 recalculation** — `monthly_contribution` is in `CALCULATION_CONTEXT_FIELDS`, so `update_goal_fields` recalculates `probability`/`on_track` via the same `calculate_goal_probability` the router's own `PATCH /goals/{id}` triggers — not a second copy of that rule. Verified: the goal effect's `after_state` includes `probability`/`on_track` (`test_apply_also_updates_a_linked_goals_monthly_contribution`).
5. **Single request-scoped transaction** — neither `update_income_source` nor `update_goal_fields` calls `db.commit()` (both call `flush()`/`refresh()` only). Combined with `record_life_event`'s no-commit discipline, the whole event — one or two entity writes, the recalculation, the LifeEvent/LifeEventEffect rows, the AuditLog row — lives in one transaction a caller's `get_db()` commits or rolls back atomically.
6. **Generic undo** — no handler-specific undo code. Both effects' `before_state`/`after_state` are built via `life_event_service.snapshot()` inside the two service functions, so the generic `undo_life_event` reverses either or both effects (in reverse order) with zero modification to the engine.
7. **Notifications** — `_LIFE_EVENT_COPY["salary_raise"]` is the one dict entry this event adds to `notification_service.py`; no new collector function.

**Why two service-layer extractions were needed before the handler could be written:**

- `planning_service.update_goal_fields()` did not exist. `routers/goals.py`'s `update_goal` had the entire ADR-001-conditional mutation inline, with no callable equivalent for a handler that isn't an HTTP request. Extracted following the same "extract, don't duplicate" pattern as `close_liability`/`update_income_source`/`update_expense` before it — the router now calls this function too, so there is exactly one implementation, verified behavior-preserving by the full pre-existing Goals/Dashboard/Reports/PlanningService suite (including the `custom_inflation_rate` edge cases that specifically exercise the conditional-recalculation branch) passing unchanged.
- `update_income_source()` returned only the `IncomeSource`, with no before/after snapshot a `LifeEventEffect` needs. Extended its return type to a 3-tuple, mirroring `close_liability`'s shape exactly; the one router call site was updated to unpack and discard the snapshots. `test_financials.py`'s full, unmodified suite (37 tests, including `test_update_income`) confirms the endpoint's externally observable behavior is unchanged.

**Bug found and fixed while building this:** `update_goal_fields`, as first extracted, called neither `session.flush()` nor `session.refresh()` after mutating the goal — unlike its two siblings (`close_liability`, `update_income_source`), which both flush (and `update_income_source` also refreshes). This was invisible through the HTTP router path (the endpoint serializes the in-memory object directly, no intervening DB read) but surfaced immediately in this event's own handler-unit tests, which call the handler directly and then `db.refresh(goal)` to assert durability — the unflushed change was silently reverted by the refresh. Root cause: `Goal.updated_at` has `onupdate=func.now()`, so a bare `flush()` alone expires that column, and a subsequent read without `refresh()` re-triggers a lazy load outside an awaited context (`MissingGreenlet`) the next time anything (e.g. FastAPI's response serialization) touches it — reproduced directly by `test_goals.py::test_update_goal` and all seven `test_goal_inflation.py` cases failing after adding `flush()` alone. Fixed by adding both `await session.flush()` and `await session.refresh(goal)`, matching `update_income_source`'s exact pattern. Full suite re-run confirms this fix, not the flush alone: 435/435 pass.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_salary_raise_handler.py` — 17 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Updates income only when no goal is linked, with a correctly-shaped `update` effect; also updates a linked goal's `monthly_contribution` and captures `probability`/`on_track` in `after_state`; ignores `goal_id` when `new_monthly_contribution` is absent (explicit opt-in); raises 404 for a nonexistent income source; raises 404 for another user's income source, with it provably untouched; raises 404 for another user's linked goal, after confirming write ordering (income written first, goal lookup fails second — atomicity itself is the rollback test's job, not this one's) |
| **Integration (full workflow)** | `record_life_event` end-to-end produces one effect (income-only) or two effects (income + goal); writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `SalaryRaiseHandler.apply()` (both writes genuinely flushed) then raises; after the caller rolls back, both the income source and the goal are back to their pre-event values, and no `LifeEvent`/`AuditLog` row exists |
| **Undo** | Reverts income only (no-goal path); reverts both income and goal, including `probability` restored to its pre-raise value; writes the generic undo `AuditLog` row; **blocked** if the income source changed independently after the event, with it left untouched; rejects undoing another user's event |
| **Dashboard / Recommendation verification** | `planning_service.get_dashboard()`'s `monthly_savings_rate` rises after a raise, called live; `family_recommendations_service.get_family_recommendations()`'s `low_savings_rate` rule (real threshold constant, not restated) fires before the raise and is confirmed absent after |

**Result:** 17/17 pass. `salary_raise_handler.py`: **100%** coverage (19 statements, 0 missed).

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`, using an income source **and** a linked goal so the test proves atomicity across *two* entity writes, not one:

1. An income source and a goal are created and committed (the pre-existing state).
2. A test-only wrapper calls the real `SalaryRaiseHandler.apply()` — both the income's `annual_amount` and the goal's `monthly_contribution` (plus its recalculated `probability`) are genuinely flushed inside the same uncommitted transaction — then raises.
3. The caller calls `db.rollback()`.
4. Verified: both the income source and the goal are back to their original values; zero `LifeEvent` rows and zero `life_event_recorded` `AuditLog` rows exist.

This is the first event in the sequence to prove the transaction-atomicity guarantee across a *compound*, two-entity write — Loan Payoff (Phase B.1) only ever touched one entity.

---

## UNDO VERIFICATION

- **Clean undo, no-goal path:** `undo_life_event` restores `annual_amount` exactly; marks the `LifeEvent` `"undone"`.
- **Clean undo, linked-goal path:** restores both `annual_amount` and `monthly_contribution`, **and** `probability` — proving the generic undo framework correctly reverses a recalculated derived field just by replaying the captured `before_state`, with no event-specific undo code.
- **Guarded/blocked undo:** after recording, the income source's `annual_amount` is independently changed; `undo_life_event` returns `blocked=True` naming `income_sources`, and leaves the row exactly as the independent edit left it.
- **Ownership:** another user cannot undo this user's Salary Raise (`LookupError`).

---

## PERFORMANCE

No new query shape beyond what `PATCH /financials/income/{id}` and `PATCH /goals/{id}` already issued. The linked-goal path adds exactly one Monte Carlo probability recalculation (`quick_probability_async`, the fast 2,000-path probe already used by every goal update) — the same cost `PATCH /goals/{id}` already incurs when a Calculation Context field changes, not a new cost this event introduces.

---

## BACKWARD COMPATIBILITY

- **Full suite: 435 passed**, zero skipped, zero failures.
- **`test_financials.py`** (37 tests, including `test_update_income`): unchanged, all pass — proves `update_income_source`'s externally observable behavior is preserved after its return-type change.
- **`test_goals.py`, `test_goal_inflation.py`, `test_planning_service.py`, `test_dashboard.py`**: unchanged, all pass — proves `update_goal_fields`'s extraction (and the flush/refresh fix) preserves `PATCH /goals/{id}`'s exact behavior, including the ADR-001 conditional-recalculation edge cases.
- **`test_notifications.py`** (12 tests, +1 new): the new life-event notification collector is additive; all pre-existing notification-source tests pass unchanged.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 68 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Salary Raise is the first compound (two-entity) event in the sequence and proves: (a) an optional, explicitly-opt-in linked step composes cleanly with the generic engine, (b) the transaction-atomicity guarantee holds across multiple entity writes in one event, (c) the generic undo framework correctly reverses a recalculated derived field with no event-specific code, and (d) the notification infrastructure (built as a prerequisite this event needed) is now in place for every subsequent event to use with a one-line `_LIFE_EVENT_COPY` addition.

Proceeding automatically to event #2 (Job Change), per standing instruction.
