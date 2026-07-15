import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.user import User
from app.schemas.financials import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
    IncomeSourceCreate,
    IncomeSourceResponse,
    IncomeSourceUpdate,
    LiabilityCreate,
    LiabilityResponse,
    LiabilityUpdate,
)
from app.services import financials_service

router = APIRouter(prefix="/financials", tags=["financials"])


# ── Income ──────────────────────────────────────────────────────────────────

@router.get("/income", response_model=list[IncomeSourceResponse])
async def list_income(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IncomeSource]:
    result = await db.execute(
        select(IncomeSource).where(
            IncomeSource.user_id == current_user.id,
            IncomeSource.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


@router.post("/income", response_model=IncomeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_income(
    body: IncomeSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncomeSource:
    # Reused by the Life Event Engine's Job Change handler — exactly one
    # implementation of "create an income source", not two.
    income, _after_state = await financials_service.create_income_source(db, current_user, body)
    return income


@router.patch("/income/{income_id}", response_model=IncomeSourceResponse)
async def update_income(
    income_id: uuid.UUID,
    body: IncomeSourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncomeSource:
    income, _before_state, _after_state = await financials_service.update_income_source(
        db, current_user, income_id, body
    )
    return income


@router.delete("/income/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income(
    income_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    # Reused by the Life Event Engine's Job Change handler — exactly one
    # implementation of "deactivate an income source", not two.
    await financials_service.deactivate_income_source(db, current_user, income_id)


# ── Expenses ─────────────────────────────────────────────────────────────────

@router.get("/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Expense]:
    result = await db.execute(
        select(Expense).where(
            Expense.user_id == current_user.id,
            Expense.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    body: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Expense:
    # Reused by the Life Event Engine's Major Medical Event handler —
    # exactly one implementation of "create an expense", not two.
    expense, _after_state = await financials_service.create_expense(db, current_user, body)
    return expense


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: uuid.UUID,
    body: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Expense:
    expense, _before_state, _after_state = await financials_service.update_expense(
        db, current_user, expense_id, body
    )
    return expense


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.user_id == current_user.id,
        )
    )
    expense = result.scalar_one_or_none()
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    expense.is_active = False
    db.add(expense)


# ── Assets ───────────────────────────────────────────────────────────────────

@router.get("/assets", response_model=list[AssetResponse])
async def list_assets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Asset]:
    result = await db.execute(
        select(Asset).where(
            Asset.user_id == current_user.id,
            Asset.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    body: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Asset:
    # Reused by the Life Event Engine's Bonus handler — exactly one
    # implementation of "create an asset", not two.
    asset, _after_state = await financials_service.create_asset(db, current_user, body)
    return asset


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Asset:
    result = await db.execute(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.user_id == current_user.id,
            Asset.is_active.is_(True),
        )
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    # Reused by the Life Event Engine's Home Sale handler — exactly one
    # implementation of "deactivate an asset", not two.
    await financials_service.deactivate_asset(db, current_user, asset_id)


# ── Liabilities ──────────────────────────────────────────────────────────────

@router.get("/liabilities", response_model=list[LiabilityResponse])
async def list_liabilities(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Liability]:
    result = await db.execute(
        select(Liability).where(
            Liability.user_id == current_user.id,
            Liability.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


@router.post("/liabilities", response_model=LiabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_liability(
    body: LiabilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Liability:
    # Reused by the Life Event Engine's New Loan handler — exactly one
    # implementation of "create a liability", not two.
    liability, _after_state = await financials_service.create_liability(db, current_user, body)
    return liability


@router.patch("/liabilities/{liability_id}", response_model=LiabilityResponse)
async def update_liability(
    liability_id: uuid.UUID,
    body: LiabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Liability:
    result = await db.execute(
        select(Liability).where(
            Liability.id == liability_id,
            Liability.user_id == current_user.id,
            Liability.is_active.is_(True),
        )
    )
    liability = result.scalar_one_or_none()
    if liability is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liability not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(liability, field, value)
    db.add(liability)
    await db.flush()
    await db.refresh(liability)
    return liability


@router.delete("/liabilities/{liability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_liability(
    liability_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    # Reused by the Life Event Engine's Loan Payoff handler
    # (Milestone 2, Phase B.1) — exactly one implementation of "close a
    # liability", not two.
    await financials_service.close_liability(db, current_user, liability_id)
