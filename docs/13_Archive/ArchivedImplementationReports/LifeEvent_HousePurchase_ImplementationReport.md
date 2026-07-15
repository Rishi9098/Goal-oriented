# LIFE EVENT ENGINE — HOUSE PURCHASE IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #5 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.7's House Purchase — a home `Asset` create + mortgage `Liability` create, with two independent optional steps: reducing an existing liquid asset for the down payment, and bumping a linked goal's `current_amount`. The largest compound event so far — up to **four** effects in one transaction. **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/financials_service.py` | Modified | Added `adjust_asset_value()` — new, minimal logic (not an extraction of an existing endpoint) that increases/decreases an existing asset's `current_value` by a delta, for events that move money into or out of an account rather than creating a new one |
| `backend/app/services/house_purchase_handler.py` | New (114 lines) | `HousePurchaseHandler` — the concrete `LifeEventHandler`, orchestrating up to four writes |
| `backend/app/main.py` | Modified | Registers `HousePurchaseHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added the one `"house_purchase"` entry to `_LIFE_EVENT_COPY` |
| `backend/tests/test_house_purchase_handler.py` | New (16 tests) | The full House Purchase test suite |

**Not touched:** everything else — the base path reuses `create_asset` (Bonus) and `create_liability` (New Loan) unmodified; the linked-goal step reuses `planning_service.update_goal_fields` (Salary Raise) unmodified.

---

## HANDLER DESIGN

```python
class HousePurchaseHandler:
    async def apply(self, db, user, inputs):
        asset, asset_after = await financials_service.create_asset(
            db, user, AssetCreate(asset_type="real_estate", ..., current_value=float(inputs["property_value"])),
        )
        effects = [EntityEffect("assets", asset.id, "create", None, asset_after)]

        liability, liability_after = await financials_service.create_liability(
            db, user, LiabilityCreate(liability_type="mortgage", ..., balance=float(inputs["mortgage_balance"])),
        )
        effects.append(EntityEffect("liabilities", liability.id, "create", None, liability_after))

        # optional: down payment (both fields required)
        if inputs.get("down_payment_asset_id") is not None and inputs.get("down_payment_amount") is not None:
            funding_asset, before, after = await financials_service.adjust_asset_value(
                db, user, uuid.UUID(inputs["down_payment_asset_id"]), -float(inputs["down_payment_amount"])
            )
            effects.append(EntityEffect("assets", funding_asset.id, "update", before, after))

        # optional: linked goal (both fields required)
        if inputs.get("goal_id") is not None and inputs.get("new_goal_current_amount") is not None:
            goal, goal_before, goal_after = await planning_service.update_goal_fields(
                db, user, uuid.UUID(inputs["goal_id"]), {"current_amount": float(inputs["new_goal_current_amount"])}
            )
            effects.append(EntityEffect("goals", goal.id, "update", goal_before, goal_after))

        return effects
```

114 lines including the module docstring, imports, and the class's own docstring. Four possible writes, all through functions the corresponding endpoints/extractions already provide.

1. **Two mandatory creates, two independent optional updates** — the home asset and mortgage liability are always created; the down-payment reduction and goal-progress bump are each independently opt-in (both fields of a pair must be present), matching the established "never assume an optional step" rule from Salary Raise and Job Change, now shown to compose with *two* independent optional steps on the same event rather than just one.
2. **`adjust_asset_value` is new logic, not an extraction** — unlike every prior service function this sequence has added, there is no existing `PATCH /financials/assets/{id}`-shaped endpoint that reduces a balance by a delta (that endpoint sets an absolute value from the request body). This function reads the current value itself so the handler only needs to know the amount of change. It is deliberately generic (`delta` can be positive or negative) because Home Sale (event #6, next) needs the identical operation in the opposite direction (adding sale proceeds) — built once, to be reused immediately by the very next event, not speculatively for a hypothetical future one.
3. **The linked-goal step reuses `planning_service.update_goal_fields` unmodified** — `current_amount` is in `CALCULATION_CONTEXT_FIELDS`, so `calculate_goal_probability` reruns for the goal exactly as `PATCH /goals/{id}` already triggers it, confirmed by the goal effect's `after_state` containing `probability`.
4. **Single request-scoped transaction across up to four writes** — none of `create_asset`, `create_liability`, `adjust_asset_value`, or `update_goal_fields` call `db.commit()`. This is the largest atomicity surface any event in this sequence has exercised.
5. **Generic undo, no event-specific code** — two `create` effects (home asset, mortgage — soft-deleted on undo) and up to two `update` effects (down-payment asset, goal — both restored via `before_state`), all through the unmodified generic engine.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_house_purchase_handler.py` — 16 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Creates the home asset and mortgage liability only (no optional steps); also reduces the down-payment asset when both fields are given; also updates a linked goal's `current_amount` (with `probability` recalculated) when both fields are given; ignores `down_payment_asset_id` without an accompanying amount; all four effects together in one call; raises 404 for a nonexistent down-payment asset |
| **Integration (full workflow)** | `record_life_event` end-to-end produces the base two effects; writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `HousePurchaseHandler.apply()` with all four writes engaged, then raises; after rollback, neither the home asset nor the mortgage exists, and both the down-payment asset and the goal are back to their original values |
| **Undo** | Reverses all four effects in one call (two soft-deletes, two restores); writes the generic undo `AuditLog` row; **blocked** if the home asset changed independently after the event; rejects undoing another user's event |
| **Dashboard / Recommendation verification** | `planning_service.get_dashboard()`'s `net_worth` rises by exactly the new equity (property value minus mortgage balance), called live — proving both the asset and liability writes landed together, not just one; `family_recommendations_service.get_family_recommendations()`'s `high_interest_debt` rule fires immediately for a high-rate mortgage |

**Result:** 16/16 pass. `house_purchase_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`, the largest atomicity proof in this sequence — four entities, two brand-new and two pre-existing:

1. A down-payment funding asset and a linked goal are created and committed (the pre-existing state).
2. A test-only wrapper calls the real `HousePurchaseHandler.apply()` with all four writes engaged — home asset create, mortgage create, funding-asset reduction, goal-progress bump — all genuinely flushed inside the uncommitted transaction — then raises.
3. The caller calls `db.rollback()`.
4. Verified: neither the home asset nor the mortgage exists; the funding asset's `current_value` and the goal's `current_amount` are both back to their original values; zero `LifeEvent`/`AuditLog` rows exist.

---

## UNDO VERIFICATION

- **Clean undo, all four effects:** `undo_life_event` soft-deletes the home asset and mortgage (generic create-effect rule) and restores the funding asset's `current_value` and the goal's `current_amount` (generic update-effect rule) — one call reversing four rows across three entity types.
- **Guarded/blocked undo:** after recording, the home asset's `current_value` is independently changed; `undo_life_event` returns `blocked=True` naming `assets`.
- **Ownership:** another user cannot undo this user's House Purchase (`LookupError`).

---

## PERFORMANCE

No new query shape beyond what the four underlying operations already issued individually — two `INSERT`s and up to two `SELECT`+`UPDATE` pairs, no N+1, no new index required.

---

## BACKWARD COMPATIBILITY

- **Full suite: 488 passed**, zero skipped, zero failures.
- **`test_financials.py`, `test_planning_service.py`, `test_goals.py`**: unchanged, all pass — `adjust_asset_value` is new logic with no existing endpoint behavior to preserve, and every reused extraction (`create_asset`, `create_liability`, `update_goal_fields`) is called identically to its own prior event.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 73 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** House Purchase proves the engine handles four effects across three entity types in one atomic transaction, and that `adjust_asset_value` — built here specifically because Home Sale needs the identical operation in reverse — is ready to be reused immediately by the next event, continuing the pattern established by New Loan reusing Bonus's `create_asset`.

Proceeding automatically to event #6 (Home Sale), per standing instruction.
