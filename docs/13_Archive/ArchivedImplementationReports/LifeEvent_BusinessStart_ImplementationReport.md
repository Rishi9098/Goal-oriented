# LIFE EVENT ENGINE — BUSINESS START IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #16 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.14's Business Start — sets `employment_status="self_employed"`, with two independent optional steps (startup costs, startup debt). **The second event in the sequence (after Adoption) requiring zero new service-layer code — entirely composed of prior events' own extractions. No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/business_start_handler.py` | New (123 lines) | `BusinessStartHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `BusinessStartHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added the one `"business_start"` entry to `_LIFE_EVENT_COPY` |
| `backend/tests/test_business_start_handler.py` | New (14 tests) | The full Business Start test suite, including an explicit test that no `IncomeSource` is ever created |

**Not touched:** every service function this event needs — `profile_service.update_profile_fields` (Job Change/Retirement), `financials_service.adjust_asset_value` (House Purchase/Home Sale/Major Medical Event), `create_expense` (Major Medical Event), `create_liability` (New Loan/House Purchase/Major Medical Event) — was already built and is reused completely unmodified.

---

## HANDLER DESIGN

```python
class BusinessStartHandler:
    async def apply(self, db, user, inputs):
        profile, before, after = await profile_service.update_profile_fields(
            db, user, {"employment_status": "self_employed"}
        )
        effects = [EntityEffect("user_profiles", profile.id, "create" if before is None else "update", before, after)]

        if inputs.get("funding_asset_id") is not None and inputs.get("funding_amount") is not None:
            asset, before, after = await financials_service.adjust_asset_value(
                db, user, uuid.UUID(inputs["funding_asset_id"]), -float(inputs["funding_amount"])
            )
            effects.append(EntityEffect("assets", asset.id, "update", before, after))

        if inputs.get("ongoing_expense_amount") is not None:
            expense, after = await financials_service.create_expense(
                db, user, ExpenseCreate(category="business", monthly_amount=float(inputs["ongoing_expense_amount"]), ...)
            )
            effects.append(EntityEffect("expenses", expense.id, "create", None, after))

        if inputs.get("loan_balance") is not None:
            liability, after = await financials_service.create_liability(
                db, user, LiabilityCreate(liability_type="other", balance=float(inputs["loan_balance"]), ...)
            )
            effects.append(EntityEffect("liabilities", liability.id, "create", None, after))

        return effects
```

123 lines including the module docstring, imports, and the class's own docstring. This event required **no new extraction at all** — every write is a direct call to a function built for a different, earlier event.

1. **No `income_sources` row, ever — by explicit design, not omission.** The architecture states this plainly: a business start commonly precedes any revenue, and inventing a `$0` `IncomeSource` would misrepresent the household's actual finances. This handler contains no code path that creates one; `test_apply_never_creates_an_income_source` locks this in directly, even when every other optional step is engaged simultaneously.
2. **Two independent optional steps, both explicit opt-in** — startup costs (`funding_asset_id`+`funding_amount` reduces an asset, `ongoing_expense_amount` creates a recurring expense — these two representations of "startup cost" are independent, not mutually exclusive, matching the architecture's "reduces a liquid Asset, or creates an Expense if ongoing" framing as two possible entity effects of the same conceptual step rather than a single either/or branch) and startup debt (`loan_balance` creates a liability).
3. **Honest schema gap, named not worked around** — `liability_type="other"` is used for a business loan since no dedicated `business_loan` enum value exists yet, with the specific label carried in `description`; verified directly by `test_apply_creates_a_business_loan_as_other_liability_type`, matching the architecture's own explicit flag of this as a known, deliberate placeholder.
4. **Single request-scoped transaction across up to four writes; generic undo, including the same named profile-create limitation Retirement's report already documented** — reused, not re-derived: `test_undo_reverses_all_effects_when_profile_pre_exists` pre-seeds a `UserProfile` row so the effect is an `update` (reversible), consistent with how that limitation is already handled in this sequence's own precedent.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table — including no `business_loan` enum addition, per the architecture's own decision to flag it as a future, additive change rather than build it now. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_business_start_handler.py` — 14 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Sets `employment_status` with no optional steps (1 effect); never creates an `IncomeSource` even with every other optional step engaged; reduces the funding asset; creates an ongoing business expense; creates a business loan as `liability_type="other"` with the specific label in `description`; all three optional steps together (4 effects, in table order) |
| **Integration (full workflow)** | `record_life_event` end-to-end; writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `BusinessStartHandler.apply()` with every optional step engaged, then raises; after rollback, the funding asset is unchanged, no expense or liability exists, and the profile does not read `self_employed` |
| **Undo** | Reverses all effects when the profile pre-exists (the common case, same as Retirement); writes the generic undo `AuditLog` row; rejects undoing another user's event |

**Result:** 14/14 pass. `business_start_handler.py`: **100%** coverage.

---

## ROLLBACK / UNDO VERIFICATION

Directly exercised across all four possible effects at once, following the identical proof shape Retirement's own report established for a multi-service, profile-touching event: a wrapper handler performs the real writes, genuinely flushed, then raises; rollback confirms none survive; undo confirms every reversible effect reverses correctly, with the same pre-existing-profile precondition Retirement's report already named as necessary for the profile effect specifically to be undoable.

---

## PERFORMANCE

No new query shape beyond what the four underlying service functions already issue individually.

---

## BACKWARD COMPATIBILITY

- **Full suite: 621 passed**, zero skipped, zero failures.
- **`test_financials.py`**: unchanged, all pass.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 84 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Business Start is the deepest reuse composition in the sequence so far — four different prior events' own extractions, wired together with zero new service code, only a new handler class expressing this event's specific combination and defaults. The one remaining event, Business Sale, is described by the architecture as a compound reversal of this event's own shape.

Proceeding automatically to event #17 (Business Sale) — the final event in the sequence — per standing instruction.
