from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.assumptions import FinancialAssumptions
from app.models.user import User
from app.schemas.assumptions import FinancialAssumptionsResponse, FinancialAssumptionsUpdate

router = APIRouter(prefix="/assumptions", tags=["assumptions"])

_DEFAULTS = {
    "inflation_rate": 0.03,
    "expected_return_conservative": 0.05,
    "expected_return_balanced": 0.07,
    "expected_return_aggressive": 0.09,
    "tax_rate": 0.22,
    "retirement_age": 65,
    "social_security_monthly": 0.0,
}


@router.get("", response_model=FinancialAssumptionsResponse)
async def get_assumptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialAssumptions:
    result = await db.execute(
        select(FinancialAssumptions).where(FinancialAssumptions.user_id == current_user.id)
    )
    assumptions = result.scalar_one_or_none()
    if assumptions is None:
        assumptions = FinancialAssumptions(user_id=current_user.id, **_DEFAULTS)
        db.add(assumptions)
        await db.flush()
        await db.refresh(assumptions)
        await db.commit()
    return assumptions


@router.put("", response_model=FinancialAssumptionsResponse)
async def upsert_assumptions(
    body: FinancialAssumptionsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialAssumptions:
    result = await db.execute(
        select(FinancialAssumptions).where(FinancialAssumptions.user_id == current_user.id)
    )
    assumptions = result.scalar_one_or_none()

    data = body.model_dump(exclude_unset=True)

    if assumptions is None:
        assumptions = FinancialAssumptions(user_id=current_user.id, **{**_DEFAULTS, **data})
        db.add(assumptions)
    else:
        for field, value in data.items():
            setattr(assumptions, field, value)
        db.add(assumptions)

    await db.flush()
    await db.refresh(assumptions)
    await db.commit()
    return assumptions
