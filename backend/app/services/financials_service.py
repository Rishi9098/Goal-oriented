"""Service layer for financial-facts entities.

Milestone 1 scope: `update_income_source` and `update_expense` (see
Milestone1ImplementationSpecification_FINAL.md §7). List/create/delete for
all four financial-facts entities, and update for Asset/Liability, remain
inline in `app.routers.financials` — that pre-existing logic is deliberately
not moved here (see the spec's §20, Rejected Decision 2, and §19,
Outstanding Risk 1).

Milestone 2 Life Event Engine, Phase B.1 addition: `close_liability` is the
one exception — extracted here (not left inline in the router) because the
Life Event Engine's Loan Payoff handler needs to call the exact same
mutation `DELETE /financials/liabilities/{id}` performs, and Phase B.1's
own requirement ("reuse the existing liability services, do not duplicate
financial calculations") means there must be exactly one implementation,
not two. `routers/financials.py`'s `delete_liability` now calls this
function too, so its own behavior is provably unchanged, not just assumed
so — see LifeEvent_PhaseB1_ImplementationReport.md.
"""

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.user import User
from app.schemas.financials import (
    AssetCreate,
    ExpenseCreate,
    ExpenseUpdate,
    IncomeSourceCreate,
    IncomeSourceUpdate,
    LiabilityCreate,
)
from app.services import life_event_service


async def create_liability(
    db: AsyncSession, current_user: User, data: LiabilityCreate
) -> tuple[Liability, dict[str, Any]]:
    """Creates a liability — the exact mutation `POST /financials/liabilities`
    performs. Returns the liability plus an after_state snapshot (via
    `life_event_service.snapshot()`) of every field just set, for a
    caller (e.g. the Life Event Engine's New Loan handler) building a
    "create" `LifeEventEffect` (before_state=None, per the engine's
    convention for creates)."""
    liability = Liability(user_id=current_user.id, **data.model_dump())
    db.add(liability)
    await db.flush()
    await db.refresh(liability)
    after_state = life_event_service.snapshot(liability, data.model_dump().keys())
    return liability, after_state


async def create_asset(
    db: AsyncSession, current_user: User, data: AssetCreate
) -> tuple[Asset, dict[str, Any]]:
    """Creates an asset — the exact mutation `POST /financials/assets`
    performs. Returns the asset plus an after_state snapshot (via
    `life_event_service.snapshot()`) of every field just set, for a
    caller (e.g. the Life Event Engine's Bonus handler) building a
    "create" `LifeEventEffect` (before_state=None, per the engine's
    convention for creates)."""
    asset = Asset(user_id=current_user.id, **data.model_dump())
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    after_state = life_event_service.snapshot(asset, data.model_dump().keys())
    return asset, after_state


async def adjust_asset_value(
    db: AsyncSession, current_user: User, asset_id: uuid.UUID, delta: float
) -> tuple[Asset, dict[str, Any], dict[str, Any]]:
    """Increases or decreases an existing liquid asset's `current_value`
    by `delta` (negative to subtract, e.g. a down payment; positive to
    add, e.g. sale proceeds) — used by events that move money into or
    out of an existing account rather than creating a new one outright.
    Not a duplicate of a PATCH-style update: the caller only needs to
    know the amount of change, not the resulting total, since this
    function reads the current value itself. No existing router endpoint
    performs this exact mutation (`PATCH /financials/assets/{id}` sets an
    absolute value from the request body), so there is nothing to extract
    from — this is new, minimal logic specific to the Life Event Engine's
    own domain (House Purchase's down payment, Home Sale's proceeds).

    Locked with `with_for_update()` (LifeEventEngine_FinalReleaseAudit.md
    §4.3): this is a read-modify-write on `current_value` — two
    concurrent calls (e.g. a duplicate submission racing a legitimate
    edit, or two life events both funded from the same account) must not
    both read the same starting value and silently lose one delta. A row
    lock under Postgres (production) serializes the second caller behind
    the first; silently ignored by SQLite (this test suite's backend,
    which has no row-level locking) — see this module's own test
    coverage for how that gap is bridged."""
    result = await db.execute(
        select(Asset)
        .where(Asset.id == asset_id, Asset.user_id == current_user.id, Asset.is_active.is_(True))
        .with_for_update()
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    fields = ("current_value",)
    before_state = life_event_service.snapshot(asset, fields)
    asset.current_value = asset.current_value + delta
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    after_state = life_event_service.snapshot(asset, fields)
    return asset, before_state, after_state


# Snapshotted fields for an asset's deactivate effect — the same
# undo-safety rationale as _LIABILITY_UNDO_SNAPSHOT_FIELDS: capturing more
# than just is_active means an independent edit to the value is still
# detected as "changed since this event" by undo's guard.
_ASSET_UNDO_SNAPSHOT_FIELDS = ("is_active", "current_value")


async def deactivate_asset(
    db: AsyncSession, current_user: User, asset_id: uuid.UUID
) -> tuple[Asset, dict[str, Any], dict[str, Any]]:
    """Soft-deletes an asset — the exact mutation
    `DELETE /financials/assets/{id}` performs. Returns the asset plus a
    before/after snapshot of the fields relevant to undo safety,
    mirroring `deactivate_income_source`'s shape exactly."""
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == current_user.id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    before_state = life_event_service.snapshot(asset, _ASSET_UNDO_SNAPSHOT_FIELDS)
    asset.is_active = False
    db.add(asset)
    await db.flush()
    after_state = life_event_service.snapshot(asset, _ASSET_UNDO_SNAPSHOT_FIELDS)
    return asset, before_state, after_state


# Snapshotted fields for an income source's create/deactivate effects — the
# same undo-safety rationale as _LIABILITY_UNDO_SNAPSHOT_FIELDS below:
# capturing more than just is_active means an independent edit to the
# amount is still detected as "changed since this event" by undo's guard.
_INCOME_SOURCE_UNDO_SNAPSHOT_FIELDS = ("is_active", "annual_amount")


async def create_income_source(
    db: AsyncSession, current_user: User, data: IncomeSourceCreate
) -> tuple[IncomeSource, dict[str, Any]]:
    """Creates an income source — the exact mutation
    `POST /financials/income` performs. Returns the income source plus an
    after_state snapshot (via `life_event_service.snapshot()`) of every
    field just set, for a caller (e.g. the Life Event Engine's Job Change
    handler) building a "create" `LifeEventEffect` (before_state=None, per
    the engine's convention for creates)."""
    income = IncomeSource(user_id=current_user.id, **data.model_dump())
    db.add(income)
    await db.flush()
    await db.refresh(income)
    after_state = life_event_service.snapshot(income, data.model_dump().keys())
    return income, after_state


async def deactivate_income_source(
    db: AsyncSession, current_user: User, income_id: uuid.UUID
) -> tuple[IncomeSource, dict[str, Any], dict[str, Any]]:
    """Soft-deletes an income source — the exact mutation
    `DELETE /financials/income/{id}` performs. Returns the income source
    plus a before/after snapshot of the fields relevant to undo safety,
    mirroring `close_liability`'s shape exactly."""
    result = await db.execute(
        select(IncomeSource).where(
            IncomeSource.id == income_id, IncomeSource.user_id == current_user.id
        )
    )
    income = result.scalar_one_or_none()
    if income is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Income source not found"
        )

    before_state = life_event_service.snapshot(income, _INCOME_SOURCE_UNDO_SNAPSHOT_FIELDS)
    income.is_active = False
    db.add(income)
    await db.flush()
    await db.refresh(income)
    after_state = life_event_service.snapshot(income, _INCOME_SOURCE_UNDO_SNAPSHOT_FIELDS)
    return income, before_state, after_state


async def update_income_source(
    db: AsyncSession,
    current_user: User,
    income_id: uuid.UUID,
    patch: IncomeSourceUpdate,
) -> tuple[IncomeSource, dict[str, Any], dict[str, Any]]:
    """Updates an income source — the exact mutation
    `PATCH /financials/income/{id}` performs. Returns the income source
    plus a before/after snapshot (via `life_event_service.snapshot()`) of
    only the fields this call actually touched, for a caller (e.g. the
    Life Event Engine's Salary Raise handler) building a `LifeEventEffect`.
    """
    result = await db.execute(
        select(IncomeSource).where(
            IncomeSource.id == income_id,
            IncomeSource.user_id == current_user.id,
            IncomeSource.is_active.is_(True),
        )
    )
    income = result.scalar_one_or_none()
    if income is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Income source not found"
        )
    updates = patch.model_dump(exclude_unset=True)
    before_state = life_event_service.snapshot(income, updates.keys())
    for field, value in updates.items():
        setattr(income, field, value)
    db.add(income)
    await db.flush()
    await db.refresh(income)
    after_state = life_event_service.snapshot(income, updates.keys())
    return income, before_state, after_state


async def create_expense(
    db: AsyncSession, current_user: User, data: ExpenseCreate
) -> tuple[Expense, dict[str, Any]]:
    """Creates an expense — the exact mutation `POST /financials/expenses`
    performs. Returns the expense plus an after_state snapshot (via
    `life_event_service.snapshot()`) of every field just set, for a
    caller (e.g. the Life Event Engine's Major Medical Event handler)
    building a "create" `LifeEventEffect` (before_state=None, per the
    engine's convention for creates)."""
    expense = Expense(user_id=current_user.id, **data.model_dump())
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    after_state = life_event_service.snapshot(expense, data.model_dump().keys())
    return expense, after_state


async def update_expense(
    db: AsyncSession,
    current_user: User,
    expense_id: uuid.UUID,
    patch: ExpenseUpdate,
) -> tuple[Expense, dict[str, Any], dict[str, Any]]:
    """Updates an expense — the exact mutation `PATCH /financials/
    expenses/{id}` performs. Returns the expense plus a before/after
    snapshot (via `life_event_service.snapshot()`) of only the fields
    this call actually touched, mirroring `update_income_source`'s shape
    exactly."""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.user_id == current_user.id,
            Expense.is_active.is_(True),
        )
    )
    expense = result.scalar_one_or_none()
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    updates = patch.model_dump(exclude_unset=True)
    before_state = life_event_service.snapshot(expense, updates.keys())
    for field, value in updates.items():
        setattr(expense, field, value)
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    after_state = life_event_service.snapshot(expense, updates.keys())
    return expense, before_state, after_state


# Snapshotted both before and after closing, for the Loan Payoff handler's
# undo safety — not just `is_active`, so a concurrent balance/rate/payment
# edit (however unlikely once a liability is closed and no longer visible
# to `update_liability`'s own is_active filter) would still be detected as
# "changed since this event", never silently discarded by an undo.
_LIABILITY_UNDO_SNAPSHOT_FIELDS = ("is_active", "balance", "interest_rate", "monthly_payment")


async def close_liability(
    db: AsyncSession, current_user: User, liability_id: uuid.UUID
) -> tuple[Liability, dict[str, Any], dict[str, Any]]:
    """Closes (soft-deletes) a liability. Returns the liability plus a
    before/after snapshot of the fields relevant to undo safety, built via
    `life_event_service.snapshot()` so a caller's `EntityEffect` uses the
    identical serialization undo's conflict check expects.

    Deliberately no `is_active` filter on the lookup, matching
    `DELETE /financials/liabilities/{id}`'s pre-existing query exactly (not
    `update_liability`'s, which does filter) — the original endpoint
    tolerates being called on an already-inactive row as a harmless no-op
    re-deactivation, and this extraction must not change that observable
    behavior."""
    result = await db.execute(
        select(Liability).where(
            Liability.id == liability_id,
            Liability.user_id == current_user.id,
        )
    )
    liability = result.scalar_one_or_none()
    if liability is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liability not found")

    before_state = life_event_service.snapshot(liability, _LIABILITY_UNDO_SNAPSHOT_FIELDS)
    liability.is_active = False
    db.add(liability)
    await db.flush()
    after_state = life_event_service.snapshot(liability, _LIABILITY_UNDO_SNAPSHOT_FIELDS)
    return liability, before_state, after_state
