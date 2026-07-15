# LIFE EVENT ENGINE — NEW LOAN IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #4 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.9's New Loan — a `Liability` create, with an optional linked `Asset` create ("what did this loan fund?") for symmetry with House Purchase, never mandatory. **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/financials_service.py` | Modified | Added `create_liability()` — the exact mutation `POST /financials/liabilities` performs, returning an after_state snapshot for a `LifeEventEffect` |
| `backend/app/routers/financials.py` | Modified | `create_liability` endpoint now calls `financials_service.create_liability()` instead of its own inline mutation |
| `backend/app/services/new_loan_handler.py` | New (78 lines) | `NewLoanHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `NewLoanHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added the one `"new_loan"` entry to `_LIFE_EVENT_COPY` |
| `backend/tests/test_new_loan_handler.py` | New (16 tests) | The full New Loan test suite |

**Not touched:** everything else — New Loan reuses `create_asset` (already extracted for Bonus) unmodified for its optional linked-purchase step.

---

## HANDLER DESIGN

```python
class NewLoanHandler:
    async def apply(self, db, user, inputs):
        raw_interest_rate = inputs.get("interest_rate")
        liability, liability_after = await financials_service.create_liability(
            db, user, LiabilityCreate(
                liability_type=inputs["liability_type"],
                institution=inputs.get("institution"),
                description=inputs.get("description"),
                balance=float(inputs["balance"]),
                interest_rate=float(raw_interest_rate) if raw_interest_rate is not None else None,
                monthly_payment=float(inputs.get("monthly_payment", 0.0)),
            ),
        )
        effects = [EntityEffect("liabilities", liability.id, "create", None, liability_after)]

        asset_type = inputs.get("asset_type")
        asset_value = inputs.get("asset_value")
        if asset_type is not None and asset_value is not None:
            asset, asset_after = await financials_service.create_asset(
                db, user, AssetCreate(
                    asset_type=asset_type,
                    institution=inputs.get("asset_institution"),
                    description=inputs.get("asset_description", "Financed purchase"),
                    current_value=float(asset_value),
                ),
            )
            effects.append(EntityEffect("assets", asset.id, "create", None, asset_after))
        return effects
```

78 lines including the module docstring, imports, and the class's own docstring. It computes nothing: both writes go through functions the corresponding `POST /financials/liabilities` and `POST /financials/assets` endpoints already call — the second of which (`create_asset`) was already extracted for the Bonus event and is reused here completely unmodified, the first time in this sequence a prior event's own extraction has been reused by a later one without any change.

1. **No existence validation needed** — like Bonus, both are creates; there is no id to look up ownership for.
2. **Optional linked asset, explicit opt-in only** — the asset step fires only when *both* `asset_type` and `asset_value` are present, mirroring Salary Raise's and Job Change's "never assume an optional step" rule exactly. Tested explicitly (`test_apply_ignores_asset_type_when_asset_value_is_absent`).
3. **Sensible defaults for optional loan terms** — `monthly_payment` defaults to `0.0` and `interest_rate` may be omitted entirely (`None`), matching `LiabilityCreate`'s own schema defaults; the handler doesn't invent stricter requirements than the underlying schema already has.
4. **Single request-scoped transaction** — neither `create_liability` nor `create_asset` calls `db.commit()`.
5. **Generic undo, no event-specific code** — both effects are `create` with `before_state=None`; undo soft-deletes each (the liability and, if present, the linked asset) via the same generic rule Job Change's and Bonus's create-effects already exercised — now proven across three different entity types (`income_sources`, `assets`, `liabilities`) with zero engine changes.
6. **`high_interest_debt` reflects a high-rate new loan immediately** — no new logic: `family_recommendations_service` reads `liabilities` live, so a 24% APR credit card recorded via this event appears in the very next `get_family_recommendations()` call, verified directly against the real recommendation engine.

**Why `create_liability` was extracted:** it didn't exist — `routers/financials.py`'s `create_liability` endpoint had the mutation inline. Extracted following the identical pattern as `create_asset` (Bonus) and `create_income_source` (Job Change); the router now calls it too, verified behavior-preserving by the full, unmodified `test_financials.py` suite passing unchanged.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_new_loan_handler.py` — 16 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Creates a liability only when no asset is linked; also creates the linked asset when both `asset_type`/`asset_value` are given; ignores `asset_type` when `asset_value` is absent (explicit opt-in); defaults `monthly_payment` to `0.0` and allows an omitted `interest_rate` |
| **Integration (full workflow)** | `record_life_event` end-to-end produces one effect (loan-only) or two effects (loan + asset); writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `NewLoanHandler.apply()` (both writes genuinely flushed) then raises; after the caller rolls back, neither the liability nor the asset exists at all |
| **Undo** | Soft-deletes the liability only when no asset was linked; soft-deletes **both** the liability and the linked asset when one was created; writes the generic undo `AuditLog` row; **blocked** if the liability changed independently after the event; rejects undoing another user's event |
| **Dashboard / Recommendation verification** | `planning_service.get_dashboard()`'s `liabilities`/`net_worth` shift by exactly the new loan's balance, called live; `family_recommendations_service.get_family_recommendations()`'s `high_interest_debt` rule (real threshold constant, not restated) is absent before a high-rate loan is recorded and present immediately after |

**Result:** 16/16 pass. `new_loan_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`, using both the loan and its linked asset so the test proves atomicity across two brand-new rows, neither with prior state to restore:

1. A test-only wrapper calls the real `NewLoanHandler.apply()` — both the liability and the linked asset are genuinely flushed inside the uncommitted transaction — then raises.
2. The caller calls `db.rollback()`.
3. Verified: neither the liability nor the asset exists for this user; zero `LifeEvent`/`AuditLog` rows exist.

---

## UNDO VERIFICATION

- **Clean undo, loan-only path:** `undo_life_event` soft-deletes the liability via the generic create-effect rule.
- **Clean undo, loan+asset path:** soft-deletes both rows — the third distinct entity type (after `income_sources` in Job Change, `assets` in Bonus) this exact generic rule has now correctly reversed with zero event-specific code.
- **Guarded/blocked undo:** after recording, the liability's `balance` is independently changed; `undo_life_event` returns `blocked=True` naming `liabilities`.
- **Ownership:** another user cannot undo this user's New Loan (`LookupError`).

---

## PERFORMANCE

No new query shape beyond what `POST /financials/liabilities` and `POST /financials/assets` already issued individually — one or two `INSERT`s, no N+1, no new index required.

---

## BACKWARD COMPATIBILITY

- **Full suite: 473 passed**, zero skipped, zero failures.
- **`test_financials.py`** (37 tests, including its Liability cases): unchanged, all pass — proves `create_liability`'s extraction preserves the endpoint's exact externally observable behavior.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 72 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** New Loan is the first event to reuse a prior event's own service-layer extraction (`create_asset`, built for Bonus) completely unmodified, confirming the extraction pattern genuinely composes across events rather than needing a bespoke variant each time. It also proves the "create effect → soft-delete on undo" generic rule now holds for all three entity types this sequence has created so far (`income_sources`, `assets`, `liabilities`).

Proceeding automatically to event #5 (House Purchase), per standing instruction.
