# LIFE EVENT ENGINE — HOME SALE IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #6 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.8's Home Sale — the home `Asset` soft-deleted, its mortgage `Liability` soft-deleted if paid off by the sale, and net proceeds directed to a liquid asset (existing or new). **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/financials_service.py` | Modified | Added `deactivate_asset()` — the exact mutation `DELETE /financials/assets/{id}` performs, mirroring `deactivate_income_source`'s shape |
| `backend/app/routers/financials.py` | Modified | `delete_asset` endpoint now calls `financials_service.deactivate_asset()` instead of its own inline mutation |
| `backend/app/services/home_sale_handler.py` | New (98 lines) | `HomeSaleHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `HomeSaleHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added the one `"home_sale"` entry to `_LIFE_EVENT_COPY` |
| `backend/tests/test_home_sale_handler.py` | New (16 tests) | The full Home Sale test suite |

**Not touched:** everything else — this event reuses `close_liability` (Loan Payoff), `adjust_asset_value` and `create_asset` (House Purchase / Bonus) completely unmodified, the second event in a row to do so.

---

## HANDLER DESIGN

```python
class HomeSaleHandler:
    async def apply(self, db, user, inputs):
        home_asset, home_before, home_after = await financials_service.deactivate_asset(
            db, user, uuid.UUID(inputs["home_asset_id"])
        )
        effects = [EntityEffect("assets", home_asset.id, "soft_delete", home_before, home_after)]

        mortgage_liability_id = inputs.get("mortgage_liability_id")
        if mortgage_liability_id is not None and inputs.get("payoff_mortgage", True):
            liability, before, after = await financials_service.close_liability(
                db, user, uuid.UUID(mortgage_liability_id)
            )
            effects.append(EntityEffect("liabilities", liability.id, "soft_delete", before, after))

        net_proceeds = float(inputs["net_proceeds"])
        proceeds_asset_id = inputs.get("proceeds_asset_id")
        if proceeds_asset_id is not None:
            asset, before, after = await financials_service.adjust_asset_value(
                db, user, uuid.UUID(proceeds_asset_id), net_proceeds
            )
            effects.append(EntityEffect("assets", asset.id, "update", before, after))
        else:
            asset, after = await financials_service.create_asset(
                db, user, AssetCreate(asset_type=inputs.get("proceeds_asset_type", "savings"), ...)
            )
            effects.append(EntityEffect("assets", asset.id, "create", None, after))

        return effects
```

98 lines including the module docstring, imports, and the class's own docstring. Every write goes through a function an existing endpoint or a *prior event's own extraction* already provides — this is the first handler in the sequence built almost entirely from reuse: only `deactivate_asset` is new, and even that is a direct structural mirror of `deactivate_income_source` (Job Change).

1. **Mandatory: sell the home, direct the proceeds.** `home_asset_id` and `net_proceeds` are always required; the home is always soft-deleted and the proceeds always land somewhere (existing or new liquid asset) — there is no valid Home Sale with no proceeds destination.
2. **Optional mortgage payoff defaults to "yes if one exists"** — exactly as the architecture specifies: passing `mortgage_liability_id` alone pays it off; passing it with `payoff_mortgage=False` leaves it untouched (the "assumable loan" case the architecture explicitly names as rare-but-real). Tested explicitly (`test_apply_leaves_the_mortgage_untouched_when_payoff_mortgage_is_false`).
3. **Proceeds destination is a plain either/or, not two independent opt-ins** — `proceeds_asset_id` present means "add to this existing asset" (via `adjust_asset_value`, reused unmodified from House Purchase, this time with a *positive* delta — proving the function's bidirectional design was the right call, not speculative); its absence means "create a new one" (via `create_asset`, reused unmodified from Bonus).
4. **`close_liability` reused unmodified from Loan Payoff** — the very first event in this entire sequence's own extraction, now called by a fifth event with zero changes, the deepest reuse chain so far.
5. **Single request-scoped transaction across up to three writes** — none of `deactivate_asset`, `close_liability`, `adjust_asset_value`, or `create_asset` call `db.commit()`.
6. **Generic undo, no event-specific code** — a `soft_delete` effect (home, and mortgage if paid off) restores via `before_state`; an `update` or `create` proceeds effect restores or soft-deletes accordingly — all three effect shapes this event can produce are already-proven generic rules.

**Why `deactivate_asset` was extracted:** it didn't exist — `routers/financials.py`'s `delete_asset` endpoint had the mutation inline (and, notably, without even a `flush()`, unlike its sibling `deactivate_income_source`). Extracted following the identical pattern, adding the missing `flush()` the router's inline version never had (harmless there since `get_db()` commits at request end regardless, but required here for the handler's own subsequent reads within the same transaction). Verified behavior-preserving by the full, unmodified `test_financials.py` suite passing unchanged.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_home_sale_handler.py` — 16 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Sells the home, pays off the mortgage, and creates a new proceeds asset (3 effects); adds proceeds to an existing liquid asset instead (2 effects, `update`); leaves the mortgage untouched when `payoff_mortgage=False`; produces only 2 effects when no mortgage is linked at all; raises 404 for a nonexistent home asset |
| **Integration (full workflow)** | `record_life_event` end-to-end produces all three effects when a mortgage is linked; writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `HomeSaleHandler.apply()` with all three writes engaged, then raises; after rollback, the home and mortgage are both still active and the existing proceeds asset's value is unchanged |
| **Undo** | Reverses all three effects in one call (two reactivations, one value restore); writes the generic undo `AuditLog` row; **blocked** if the home asset changed independently after the event; rejects undoing another user's event |
| **Dashboard / Recommendation verification** | `planning_service.get_dashboard()`'s `liabilities` drops by the mortgage balance and `net_worth` reflects the net effect (home value out, mortgage cleared, proceeds in) precisely, called live; `family_recommendations_service.get_family_recommendations()`'s `high_interest_debt` rule stops firing once the high-rate mortgage is paid off by the sale |

**Result:** 16/16 pass. `home_sale_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`, spanning three pre-existing entities (home, mortgage, an existing liquid asset receiving proceeds):

1. A home, a mortgage, and a liquid savings asset are created and committed (the pre-existing state).
2. A test-only wrapper calls the real `HomeSaleHandler.apply()` — the home is soft-deleted, the mortgage soft-deleted, and the savings asset's value increased, all genuinely flushed inside the uncommitted transaction — then raises.
3. The caller calls `db.rollback()`.
4. Verified: the home and mortgage are both still active with original values; the savings asset's value is unchanged; zero `LifeEvent` rows exist.

---

## UNDO VERIFICATION

- **Clean undo, all three effects:** `undo_life_event` reactivates the home and mortgage (generic soft-delete-effect rule, restoring the mortgage's exact `balance`/`interest_rate`/`monthly_payment` via `close_liability`'s own undo-safety snapshot fields) and restores the proceeds asset's prior value (generic update-effect rule).
- **Guarded/blocked undo:** after recording, the home asset's `current_value` is independently changed; `undo_life_event` returns `blocked=True` naming `assets`.
- **Ownership:** another user cannot undo this user's Home Sale (`LookupError`).

---

## PERFORMANCE

No new query shape beyond what the underlying operations already issued individually — one to three `SELECT`+`UPDATE`/`INSERT` operations, no N+1, no new index required.

---

## BACKWARD COMPATIBILITY

- **Full suite: 502 passed**, zero skipped, zero failures.
- **`test_financials.py`** (37 tests, including its Asset delete cases): unchanged, all pass — proves `deactivate_asset`'s extraction preserves the endpoint's exact externally observable behavior.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 74 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Home Sale is the first handler built almost entirely from reuse — only one small extraction (`deactivate_asset`) was new, while `close_liability`, `adjust_asset_value`, and `create_asset` were all pulled in unmodified from three different prior events (Loan Payoff, House Purchase, Bonus). This confirms the "extract, don't duplicate" pattern compounds correctly as the catalog grows: later events increasingly become compositions of earlier ones rather than each needing fresh service-layer work.

Proceeding automatically to event #7 (Marriage), per standing instruction.
