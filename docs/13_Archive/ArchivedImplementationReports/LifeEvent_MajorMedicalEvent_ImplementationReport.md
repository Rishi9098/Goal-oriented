# LIFE EVENT ENGINE — MAJOR MEDICAL EVENT IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #15 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.13's Major Medical Event — a healthcare `Expense` create-or-update, with two independent optional steps: reducing a liquid asset for a lump-sum payment, and financing with a new liability. **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/financials_service.py` | Modified | Added `create_expense()`; extended `update_expense()` to return a before/after snapshot tuple (previously returned only the bare `Expense`, a Milestone 1-era gap this event's `LifeEventEffect` needs closed) |
| `backend/app/routers/financials.py` | Modified | `create_expense`/`update_expense` endpoints updated to call the new/changed service functions |
| `backend/app/services/major_medical_event_handler.py` | New (117 lines) | `MajorMedicalEventHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `MajorMedicalEventHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added the one `"major_medical_event"` entry to `_LIFE_EVENT_COPY` |
| `backend/tests/test_major_medical_event_handler.py` | New (17 tests) | The full Major Medical Event test suite |

**Not touched:** `adjust_asset_value` (House Purchase/Home Sale) and `create_liability` (New Loan) — both reused completely unmodified for this event's two optional steps.

---

## HANDLER DESIGN

```python
class MajorMedicalEventHandler:
    async def apply(self, db, user, inputs):
        monthly_amount = float(inputs["monthly_amount"])
        expense_id = inputs.get("expense_id")

        if expense_id is not None:
            expense, before, after = await financials_service.update_expense(
                db, user, uuid.UUID(expense_id), ExpenseUpdate(monthly_amount=monthly_amount)
            )
            expense_effect = EntityEffect("expenses", expense.id, "update", before, after)
        else:
            expense, after = await financials_service.create_expense(
                db, user, ExpenseCreate(category="healthcare", monthly_amount=monthly_amount, ...)
            )
            expense_effect = EntityEffect("expenses", expense.id, "create", None, after)
        effects = [expense_effect]

        if inputs.get("lump_sum_asset_id") is not None and inputs.get("lump_sum_amount") is not None:
            funding_asset, before, after = await financials_service.adjust_asset_value(
                db, user, uuid.UUID(inputs["lump_sum_asset_id"]), -float(inputs["lump_sum_amount"])
            )
            effects.append(EntityEffect("assets", funding_asset.id, "update", before, after))

        if inputs.get("loan_balance") is not None:
            liability, after = await financials_service.create_liability(
                db, user, LiabilityCreate(liability_type="personal_loan", balance=float(inputs["loan_balance"]), ...)
            )
            effects.append(EntityEffect("liabilities", liability.id, "create", None, after))

        return effects
```

117 lines including the module docstring, imports, and the class's own docstring.

1. **Create-or-update on the same entity, chosen by input presence** — the first event in this sequence where the *mandatory* step itself branches between two different service functions (`create_expense` vs `update_expense`) depending on whether `expense_id` is given, rather than the mandatory step always being a single fixed operation. Both paths produce exactly one effect, correctly typed (`create` vs `update`).
2. **Two independent optional steps, each explicit opt-in** — the lump-sum reduction (`adjust_asset_value`, reused unmodified from House Purchase/Home Sale — the third event to reuse this exact function) and the financing liability (`create_liability`, reused unmodified from New Loan), following the now-established "both fields of a pair required" rule.
3. **No one-time-expense concept invented** — per the architecture's own "honest schema note," `Expense` has no flag for "this is temporary." The handler records exactly what the schema supports (an ongoing `monthly_amount`); the "you'll need to edit this yourself once resolved" transparency is a confirmation-screen UI concern, not a write this handler performs or needs to.
4. **`update_expense`'s missing snapshot fixed as part of this event** — it predates the Life Event Engine (Milestone 1) and returned only the bare `Expense`, unlike its sibling `update_income_source` (fixed for Salary Raise). Extended to return `(expense, before_state, after_state)`, mirroring that exact shape; the one router call site was updated to unpack and discard the snapshots. Verified behavior-preserving by the full, unmodified `test_financials.py` suite (including `test_update_expense`) passing unchanged.
5. **Single request-scoped transaction across up to three writes; generic undo** — none of the four underlying service functions call `db.commit()`; undo reverses whichever effects were actually recorded, independently, exactly as the architecture specifies.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_major_medical_event_handler.py` — 17 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Creates a new healthcare expense by default; increases an existing one when `expense_id` is given; also reduces the lump-sum asset when both fields are given; also creates a financing liability when `loan_balance` is given; all three effects together; raises 404 for a nonexistent `expense_id` |
| **Integration (full workflow)** | `record_life_event` end-to-end produces the base effect; writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `MajorMedicalEventHandler.apply()` with all three writes engaged, then raises; after rollback, no expense or liability exists and the funding asset's value is unchanged |
| **Undo** | Reverses all effects (soft-deletes the expense and liability, restores the funding asset's value); writes the generic undo `AuditLog` row; **blocked** if the expense changed independently after the event; rejects undoing another user's event |
| **Dashboard / Recommendation verification** | `planning_service.get_dashboard()`'s `monthly_savings_rate` drops after a large new medical expense, called live; `family_recommendations_service.get_family_recommendations()`'s `low_savings_rate` rule (real threshold constant, not restated) fires after a sufficiently large expense is recorded |

**Result:** 17/17 pass. `major_medical_event_handler.py`: **100%** coverage.

---

## ROLLBACK / UNDO VERIFICATION

Directly exercised across all three possible effects at once — a wrapper handler performs the real create-expense, asset-reduction, and liability-create writes, genuinely flushed, then raises; rollback confirms none survive; undo confirms all three reverse correctly (two generic create-effect soft-deletes, one generic update-effect restore), blocked correctly on an independent expense-state change.

---

## PERFORMANCE

No new query shape beyond what the four underlying service functions already issue individually.

---

## BACKWARD COMPATIBILITY

- **Full suite: 609 passed**, zero skipped, zero failures.
- **`test_financials.py`** (37 tests, including `test_update_expense`): unchanged, all pass — proves both the new `create_expense` and the extended `update_expense` preserve their endpoints' exact externally observable behavior.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 83 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Major Medical Event closes the last Milestone 1-era gap in the financials service layer (`update_expense`'s missing snapshot) and demonstrates the pattern's continued reuse depth: three of its four possible writes (`update_expense`'s fixed shape aside) go through functions built for entirely different, earlier events (Bonus/House Purchase/Home Sale's `adjust_asset_value`, New Loan's `create_liability`) with zero changes.

Proceeding automatically to event #16 (Business Start), per standing instruction.
