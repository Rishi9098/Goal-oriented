# LIFE EVENT ENGINE — RETIREMENT IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #12 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.12's Retirement — described by the architecture itself as "the most structurally distinct event... touching Profile, Income, and Assumptions together." Sets `employment_status="retired"`, deactivates given salary income sources, and offers three independent opt-in steps (pension creation, assumptions update, goal-contribution updates). **The largest and most compound event in the sequence so far — 1 to 7 effects. No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/assumptions_service.py` | New | `update_assumptions_fields()` — the exact create-or-update mutation `PUT /assumptions` performs, extracted so it can be called with just the fields a handler is touching, mirroring `profile_service.update_profile_fields`'s pattern exactly |
| `backend/app/routers/assumptions.py` | Modified | `upsert_assumptions` now calls `assumptions_service.update_assumptions_fields()`; `_DEFAULTS` moved into the service module (`get_assumptions` imports it back) so there is one source of truth for both |
| `backend/app/services/retirement_handler.py` | New (137 lines) | `RetirementHandler` — the concrete `LifeEventHandler`, orchestrating up to seven writes across four services |
| `backend/app/main.py` | Modified | Registers `RetirementHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added the one `"retirement"` entry to `_LIFE_EVENT_COPY` |
| `backend/tests/test_retirement_handler.py` | New (17 tests) | The full Retirement test suite, including a named test for a real undo limitation this event surfaced |

**Not touched:** `financials_service.py`, `planning_service.py` — every entity write this event needs (`deactivate_income_source`, `create_income_source`, `update_goal_fields`) was already built by prior events and is reused completely unmodified.

---

## HANDLER DESIGN

```python
class RetirementHandler:
    async def apply(self, db, user, inputs):
        profile, before, after = await profile_service.update_profile_fields(
            db, user, {"employment_status": "retired"}
        )
        effects = [EntityEffect("user_profiles", profile.id, "create" if before is None else "update", before, after)]

        for income_id in inputs.get("income_source_ids", []):
            income, before, after = await financials_service.deactivate_income_source(db, user, uuid.UUID(income_id))
            effects.append(EntityEffect("income_sources", income.id, "soft_delete", before, after))

        if inputs.get("pension_amount") is not None:
            pension, after = await financials_service.create_income_source(db, user, IncomeSourceCreate(source_type="pension", ...))
            effects.append(EntityEffect("income_sources", pension.id, "create", None, after))

        assumptions_updates = {k: v for k in ("retirement_age", "social_security_monthly") if inputs.get(k) is not None ...}
        if assumptions_updates:
            assumptions, before, after = await assumptions_service.update_assumptions_fields(db, user, assumptions_updates)
            effects.append(EntityEffect("financial_assumptions", assumptions.id, "create" if before is None else "update", before, after))

        for goal_update in inputs.get("goal_contributions", []):
            goal, before, after = await planning_service.update_goal_fields(db, user, uuid.UUID(goal_update["goal_id"]), {"monthly_contribution": ...})
            effects.append(EntityEffect("goals", goal.id, "update", before, after))

        return effects
```

137 lines including the module docstring, imports, and the class's own docstring. Every write goes through a function four different services already provide — `profile_service` (Job Change), `financials_service` (Bonus/Job Change), `assumptions_service` (new, mirroring `profile_service`'s own pattern exactly), and `planning_service` (Salary Raise).

1. **Multiple items per optional category, not just single pairs.** Every prior event's optional steps were single opt-in pairs (one linked goal, one linked asset). Retirement is the first event where a step is a **list**: `income_source_ids` (zero or more salary sources to deactivate) and `goal_contributions` (zero or more goal updates), each producing one effect per list item. The handler loops rather than assuming a fixed cardinality, matching the architecture's own "3 to 7 effects depending on how many optional steps were taken" framing precisely — verified by `test_apply_all_steps_together_produces_up_to_seven_effects` exercising all seven at once (profile + 2 income deactivations + 1 pension create + 1 assumptions update + 2 goal updates).
2. **`assumptions_service.update_assumptions_fields` is a new extraction, not a duplicate** — `routers/assumptions.py`'s `upsert_assumptions` had this mutation inline; extracted following the identical pattern `profile_service.update_profile_fields` already established (accepts a partial dict, not a full schema instance, so a handler can update just `retirement_age`/`social_security_monthly` without touching the other five assumption fields). The router's own `_DEFAULTS` dict moved into the new service module rather than being duplicated, so `get_assumptions`'s pre-existing (and deliberately untouched) concurrency-guarded first-access path still uses the identical default values.
3. **`calculate_goal_probability` reruns only for a goal whose `monthly_contribution` was explicitly changed** — via the unmodified `update_goal_fields`/`CALCULATION_CONTEXT_FIELDS` machinery, never a bespoke "recompute every goal on retirement" pass, exactly as the architecture insists.
4. **Single request-scoped transaction across up to seven writes** — none of the four services' functions call `db.commit()`.
5. **Generic undo — with one real, named limitation this event surfaced** (below).

---

## NAMED LIMITATION FOUND: profile/assumptions "create" effects can't be undone

Building this event's undo tests surfaced a real gap: when a user has **no pre-existing** `UserProfile` or `FinancialAssumptions` row (both plausible for a user who never touched Settings), `RetirementHandler`'s corresponding effect is a `create` (`before_state=None`). Neither model has an `is_active` column — so the generic engine's own pre-existing rule ("create effect + `is_active` column → soft-delete on undo; otherwise, a known limitation, not resolved here") leaves the row entirely untouched by undo. Concretely: undoing a Retirement event for such a user correctly reverses every other effect (income sources, goals) but leaves `employment_status="retired"`/the assumption values in place.

This is not a new limitation invented by this event — it is `life_event_service.py`'s own long-documented gap (present since Phase A, first actually exercised for a household member by Marriage, and now exercised for a non-family entity for the first time). It is named explicitly and covered by its own test, `test_undo_cannot_reverse_a_newly_created_profile`, rather than silently glossed over or asserted incorrectly. The far more common real-world case — a user who already has a profile/assumptions row from onboarding, making both effects `update`s — undoes cleanly, and is covered by `test_undo_reverses_all_effects` using pre-seeded rows.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_retirement_handler.py` — 17 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Sets `employment_status` with no optional steps (1 effect); deactivates given income sources; creates a pension income source; updates assumptions when either field is given; updates one or more goal contributions with `probability` recalculated; all four optional categories combined produce exactly 7 effects in the documented table order |
| **Integration (full workflow)** | `record_life_event` end-to-end; writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `RetirementHandler.apply()` with every optional step engaged, then raises; after rollback, the salary is reactivated, the goal's contribution is unchanged, no pension income source exists, and the profile is not "retired" |
| **Undo** | Reverses all effects when profile/assumptions rows pre-exist (the common case); the named, tested limitation when they don't (the rare case); writes the generic undo `AuditLog` row; rejects undoing another user's event |
| **Dashboard verification** | Active income after the event is the pension alone, not the deactivated salary — proving the soft-delete genuinely removed it from the live picture |

**Result:** 17/17 pass. `retirement_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`, the widest rollback proof in this sequence — a salary income source, a retirement goal, and (implicitly) a profile and assumptions row, all engaged at once:

1. A salary and a retirement goal are created and committed (the pre-existing state).
2. A test-only wrapper calls the real `RetirementHandler.apply()` — all four optional steps engaged, everything genuinely flushed inside the uncommitted transaction — then raises.
3. The caller calls `db.rollback()`.
4. Verified: the salary is fully active again; the goal's contribution is unchanged; no pension income source exists; the profile (whether newly created or not) does not read `employment_status="retired"`; zero `LifeEvent` rows exist.

---

## PERFORMANCE

No new query shape beyond what the four underlying service functions already issue individually. Cost scales linearly with the number of income sources deactivated and goals updated — exactly the cost each individual `PATCH`/`DELETE` would already incur, summed, not a new aggregate operation.

---

## BACKWARD COMPATIBILITY

- **Full suite: 570 passed**, zero skipped, zero failures.
- **`test_financials.py`**: unchanged, all pass — proves no financials extraction changed behavior.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 80 source files.
- No existing endpoint's request/response schema, status code, or URL changed. `assumptions_service.DEFAULTS` and the router's own `_DEFAULTS` alias are identical values, verified by `get_assumptions`'s existing first-access tests passing unchanged.

---

## READY FOR THE NEXT EVENT?

**Yes.** Retirement is the first event to orchestrate four different services in one transaction and the first to use list-shaped (rather than single-pair) optional steps, both without any new engine mechanism. It also surfaced and explicitly documented a real, pre-existing limitation of the generic undo framework (non-`is_active` entities can't reverse a fresh create) rather than working around it with event-specific code, consistent with every prior event's own discipline on this point.

Proceeding automatically to event #13 (Education Planning), per standing instruction.
