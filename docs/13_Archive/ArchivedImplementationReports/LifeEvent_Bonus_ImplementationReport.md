# LIFE EVENT ENGINE — BONUS IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #3 of the 17-event sequence requested. **Bonus is not one of `LifeEventEngineArchitecture.md`'s original 15 catalogued events** — it was added to this run's ordered list. Modeled directly on Inheritance (§5.11): a one-time cash windfall that creates a liquid `Asset`, no `IncomeSource` (a bonus is not ongoing income). **No other event type was implemented.**

---

## DESIGN DECISION (not in the original 15-event catalog)

Per the progress matrix's own note, Bonus is treated as a minimal, documented extension of an already-established shape rather than a new mechanism:

- **Same entity, same cardinality as Inheritance §5.11**: one `Asset` create, nothing else.
- **Deliberately no "add to an existing asset" step.** §5.11's own "Entities changed" row for Inheritance reads only "`assets` create; optionally `income_sources` create" — Inheritance itself never merges into an existing asset either. An earlier draft of this progress matrix's note speculated Bonus might "add to an existing one"; on inspecting the actual architecture entry it's modeled on, that speculative branch was dropped — Inheritance is pure-create, so Bonus is too, avoiding an unneeded "read current balance, then patch" mutation this event has no real requirement for.
- **No `IncomeSource`.** A bonus is a one-time payment, not a recurring income stream — the same distinction §5.11 draws between the inherited asset itself and its *optional* rental-income sub-step (which Bonus has no equivalent of, since a bonus generates no ongoing income by definition).
- **Default `asset_type="savings"`** — one of `planning_service._LIQUID_ASSET_TYPES` (`{"checking", "savings", "money_market"}`), so a bonus counts as liquid for the `low_liquidity` recommendation immediately, matching how a real bonus payout lands in a bank account. Callers can override to `"brokerage"` etc. if the bonus was invested instead.

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/financials_service.py` | Modified | Added `create_asset()` — the exact mutation `POST /financials/assets` performs, returning an after_state snapshot for a `LifeEventEffect` |
| `backend/app/routers/financials.py` | Modified | `create_asset` endpoint now calls `financials_service.create_asset()` instead of its own inline mutation |
| `backend/app/services/bonus_handler.py` | New (49 lines) | `BonusHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `BonusHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added the one `"bonus"` entry to `_LIFE_EVENT_COPY` |
| `backend/tests/test_bonus_handler.py` | New (11 tests) | The full Bonus test suite |

**Not touched:** `income_sources`/`goals`/anything else — Bonus genuinely touches exactly one entity, one row.

---

## HANDLER DESIGN

```python
class BonusHandler:
    async def apply(self, db, user, inputs):
        asset, after_state = await financials_service.create_asset(
            db, user, AssetCreate(
                asset_type=inputs.get("asset_type", "savings"),
                institution=inputs.get("institution"),
                description=inputs.get("description", "Bonus"),
                current_value=float(inputs["amount"]),
            ),
        )
        return [EntityEffect("assets", asset.id, "create", None, after_state)]
```

49 lines including the module docstring, imports, and the class's own docstring — the simplest handler in the sequence so far, matching Loan Payoff's own simplicity (one entity, one write, no existence check needed since a create has nothing to look up).

1. **No validation needed beyond schema validation** — `AssetCreate`'s own Pydantic constraints (`current_value >= 0`, max length on strings) are the only checks; there is no id to verify ownership of.
2. **One effect, `change_type="create"`, `before_state=None`** — per the engine's established convention for creates (already exercised by Job Change's new-income-row effect).
3. **Single request-scoped transaction** — `create_asset` never calls `db.commit()` (flush + refresh only, since `Asset.updated_at` also has `onupdate=func.now()`).
4. **Generic undo, no event-specific code** — a `create` effect on a row with an `is_active` column is soft-deleted on undo, the same rule Job Change's new-income-row effect already exercised.

**Why `create_asset` was extracted into `financials_service.py`:** it didn't exist — `routers/financials.py`'s `create_asset` endpoint had the mutation inline, with no callable equivalent for a handler outside an HTTP request. Extracted following the same pattern as every prior extraction this sequence has used; the router now calls it too, verified behavior-preserving by the full, unmodified `test_financials.py` suite (including its `TestAssets` cases) passing unchanged.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_bonus_handler.py` — 11 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Creates a `"savings"` asset by default with the given amount; honors an explicit `asset_type`/`institution`/`description` override |
| **Integration (full workflow)** | `record_life_event` end-to-end produces one effect and creates the asset; writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `BonusHandler.apply()` (the asset genuinely flushed) then raises; after the caller rolls back, the asset does not exist at all, and no `LifeEvent`/`AuditLog` row exists |
| **Undo** | Soft-deletes the created asset (the same "create + `is_active` column → soft-delete" generic rule Job Change's new income row exercised); writes the generic undo `AuditLog` row; **blocked** if the asset's value changed independently after the event; rejects undoing another user's event |
| **Dashboard / Recommendation verification** | `planning_service.get_dashboard()`'s `net_worth` rises by exactly the bonus amount, called live; `family_recommendations_service.get_family_recommendations()`'s `low_liquidity` rule (real threshold constant, not restated) fires before the bonus and is confirmed absent after |

**Result:** 11/11 pass. `bonus_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`:

1. A test-only wrapper calls the real `BonusHandler.apply()` — the asset is genuinely flushed inside the uncommitted transaction — then raises.
2. The caller calls `db.rollback()`.
3. Verified: no asset exists for this user at all (the create was never durable); zero `LifeEvent`/`AuditLog` rows exist.

---

## UNDO VERIFICATION

- **Clean undo:** `undo_life_event` soft-deletes the created asset via the generic "create effect + `is_active` column" rule; marks the `LifeEvent` `"undone"`.
- **Guarded/blocked undo:** after recording, the asset's `current_value` is independently changed; `undo_life_event` returns `blocked=True` naming `assets`, and leaves it untouched.
- **Ownership:** another user cannot undo this user's Bonus (`LookupError`).

---

## PERFORMANCE

No new query shape beyond what `POST /financials/assets` already issued — one `INSERT`, no N+1, no new index required.

---

## BACKWARD COMPATIBILITY

- **Full suite: 458 passed**, zero skipped, zero failures.
- **`test_financials.py`** (37 tests, including its Asset cases): unchanged, all pass — proves `create_asset`'s extraction preserves the endpoint's exact externally observable behavior.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 71 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Bonus confirms the engine's existing "create effect + `is_active` → soft-delete on undo" rule generalizes cleanly to a second entity type (`assets`, after `income_sources` in Job Change), and that a non-catalog event can be added with zero new engine mechanism when it is genuinely a minimal composition of an already-modeled shape (Inheritance).

Proceeding automatically to event #4 (New Loan), per standing instruction.
