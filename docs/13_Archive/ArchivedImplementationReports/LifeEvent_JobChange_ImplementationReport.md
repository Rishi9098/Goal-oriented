# LIFE EVENT ENGINE — JOB CHANGE IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #2 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.2's Job Change — a `user_profiles.employer`/`occupation` update, the prior `income_sources` row soft-deleted, and a new `income_sources` row created for the replacement role. The first **three-entity** compound event in the sequence. **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/profile_service.py` | New | `update_profile_fields()` — the exact create-or-update mutation `PUT /profile` performs, extracted so it has exactly one implementation and can be called with a partial field set (not just a full request body) |
| `backend/app/routers/profile.py` | Modified | `upsert_profile` now calls `profile_service.update_profile_fields()` instead of its own inline create-or-update logic |
| `backend/app/services/financials_service.py` | Modified | Added `create_income_source()` and `deactivate_income_source()` — the exact mutations `POST /financials/income` and `DELETE /financials/income/{id}` perform, each returning before/after snapshots for a `LifeEventEffect` |
| `backend/app/routers/financials.py` | Modified | `create_income`/`delete_income` now call the two new service functions instead of their own inline mutations |
| `backend/app/services/job_change_handler.py` | New (75 lines) | `JobChangeHandler` — the concrete `LifeEventHandler`, orchestrating all three writes |
| `backend/app/main.py` | Modified | Registers `JobChangeHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added the one `"job_change"` entry to `_LIFE_EVENT_COPY` |
| `backend/tests/test_job_change_handler.py` | New (13 tests) | The full Job Change test suite |

**Not touched:** `family_recommendations_service.py`'s rule logic, `monte_carlo.py`, `routers/dashboard.py`, `routers/reports.py`, `routers/family.py` — confirmed by every one of their existing tests passing unchanged.

---

## HANDLER DESIGN

```python
class JobChangeHandler:
    async def apply(self, db, user, inputs):
        old_income_id = uuid.UUID(inputs["old_income_source_id"])

        profile, profile_before, profile_after = await profile_service.update_profile_fields(
            db, user, {"employer": inputs["new_employer"], "occupation": inputs["new_occupation"]},
        )
        old_income, old_before, old_after = await financials_service.deactivate_income_source(
            db, user, old_income_id
        )
        new_income, new_after = await financials_service.create_income_source(
            db, user, IncomeSourceCreate(
                source_type=inputs.get("new_source_type", "salary"),
                annual_amount=float(inputs["new_annual_amount"]),
                description=inputs.get("description"),
            ),
        )
        return [
            EntityEffect("user_profiles", profile.id,
                         "create" if profile_before is None else "update",
                         profile_before, profile_after),
            EntityEffect("income_sources", old_income.id, "soft_delete", old_before, old_after),
            EntityEffect("income_sources", new_income.id, "create", None, new_after),
        ]
```

75 lines including the module docstring, imports, and the class's own docstring. It computes nothing: all three writes go through functions the corresponding `PUT /profile`, `DELETE /financials/income/{id}`, and `POST /financials/income` endpoints already call.

1. **Validate everything referenced** — `deactivate_income_source` raises its own `HTTPException(404)` for a nonexistent or not-owned old income row, identical to what the router already raised. No second check. (`create_income_source`/`update_profile_fields` take no id to validate — a create and an upsert respectively.)
2. **Three effects, in write order** — profile first (create or update, depending on whether one existed), then the old income's soft-delete, then the new income's create. Order matters for undo, which reverses in the opposite order (new income first, then old income, then profile).
3. **The profile's `create` vs `update` distinction is handled by inspecting `profile_before`** (`None` means `update_profile_fields` created it) rather than a separate existence check — one query, not two, and consistent with `update_profile_fields`'s own return contract.
4. **Single request-scoped transaction** — none of `update_profile_fields`, `deactivate_income_source`, or `create_income_source` call `db.commit()` (all call `flush()`+`refresh()` only, since `UserProfile.updated_at` and `IncomeSource.updated_at` both have `onupdate=func.now()` — see the Salary Raise report's bug writeup for why the refresh is required, not optional). Combined with `record_life_event`'s no-commit discipline, all three writes plus the LifeEvent/LifeEventEffect/AuditLog rows live in one transaction a caller's `get_db()` commits or rolls back atomically.
5. **Generic undo, no event-specific code** — the framework already has a rule for a `create` effect with no `is_active` column (the profile, if it was created fresh: no generic reversal is possible, a known, pre-existing limitation of Phase A's engine — see `life_event_service.py`'s own comment — not something this event works around) and a rule for a `create` effect *with* an `is_active` column (the new income row: undo soft-deletes it). Both paths are exercised by this event with zero new engine code.

**Why three separate service-layer extractions were needed:** none of `profile_service.py`, `create_income_source`, or `deactivate_income_source` existed before this event — `routers/profile.py`'s upsert and `routers/financials.py`'s income create/delete all had their mutations inline, with no callable equivalent for a handler outside an HTTP request. Each was extracted following the same "extract, don't duplicate" pattern as `close_liability`/`update_income_source`/`update_goal_fields` before it: the original router endpoint now calls the extracted function too, so there is exactly one implementation of each mutation. Verified behavior-preserving by the full, unmodified `test_financials.py` suite (which includes `TestProfile`, `test_create_income`, `test_delete_income`) passing unchanged.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_job_change_handler.py` — 13 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Updates an existing profile, closes the old income, and creates the new one, with all three effects correctly shaped; creates a profile from scratch when none exists yet (`change_type="create"`, `before_state=None`); raises 404 for a nonexistent old income source; raises 404 for another user's old income source, with it provably untouched |
| **Integration (full workflow)** | `record_life_event` end-to-end produces exactly three effects in the expected table order; writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `JobChangeHandler.apply()` (all three writes genuinely flushed) then raises; after the caller rolls back, the old income is reactivated at its original amount, the profile is reverted, and the newly created income row does not exist at all — proving atomicity across three entities, one of which (the new income row) has no pre-existing state to roll back to |
| **Undo** | Reactivates the old income, **soft-deletes the new income** (proving the generic "create effect + `is_active` column → soft-delete on undo" rule), and reverts the profile's employer/occupation; writes the generic undo `AuditLog` row; **blocked** if the old income changed independently after the event; rejects undoing another user's event |
| **Dashboard verification** | `planning_service.get_dashboard()`'s `monthly_savings_rate` reflects only the new role's income, not both — proving the old row is genuinely deactivated rather than merely supplemented |

**Result:** 13/13 pass. `job_change_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`, the first rollback proof in this sequence spanning three entities, one of them a brand-new row with no prior state:

1. An old income source and a profile are created and committed (the pre-existing state).
2. A test-only wrapper calls the real `JobChangeHandler.apply()` — the profile is updated, the old income deactivated, and a new income row created, all genuinely flushed inside the same uncommitted transaction — then raises.
3. The caller calls `db.rollback()`.
4. Verified: the old income source is fully reactivated at its original amount; the profile is back to its original employer/occupation; **the new income row created inside the failed attempt does not exist** (only the original row remains for this user); zero `LifeEvent`/`AuditLog` rows exist.

This confirms the transaction-atomicity guarantee extends correctly to a freshly `INSERT`ed row with no `before_state` to restore — SQLAlchemy's flush-then-rollback simply discards the pending insert entirely, which is the correct behavior and required no special handling in either the handler or the engine.

---

## UNDO VERIFICATION

- **Clean undo:** `undo_life_event` reactivates the old income at its original `annual_amount`, reverts the profile's `employer`/`occupation`, and — the interesting case — **soft-deletes the newly created income row**, purely because that row's effect has `before_state=None` and the row has an `is_active` column; the generic engine's existing rule for this case (documented in Phase A, never exercised by a real event until now) handles it correctly with zero new code.
- **Guarded/blocked undo:** after recording, the old (closed) income's `annual_amount` is independently changed; `undo_life_event` returns `blocked=True` naming `income_sources`, and leaves all three rows exactly as they were.
- **Ownership:** another user cannot undo this user's Job Change (`LookupError`).

---

## PERFORMANCE

No new query shape beyond what `PUT /profile`, `DELETE /financials/income/{id}`, and `POST /financials/income` already issued individually. Three writes instead of one or two (Salary Raise), each a single-row operation — no N+1, no new index required.

---

## BACKWARD COMPATIBILITY

- **Full suite: 447 passed**, zero skipped, zero failures.
- **`test_financials.py`** (37 tests, including `TestProfile`, `test_create_income`, `test_delete_income`): unchanged, all pass — proves all three extractions preserve their endpoints' exact externally observable behavior.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 70 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Job Change is the first three-entity compound event in the sequence and proves: (a) atomicity holds across a mix of update/soft-delete/create effects in a single transaction, including a brand-new row with no prior state, (b) the generic undo framework's already-designed-but-previously-unexercised "create + no before_state + has `is_active`" reversal rule works correctly on the first real event to hit it, and (c) three independent service-layer extractions (`profile_service.py`, `create_income_source`, `deactivate_income_source`) compose cleanly without any handler-side duplication.

Proceeding automatically to event #3 (Bonus), per standing instruction.
