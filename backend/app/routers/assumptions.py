from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.assumptions import FinancialAssumptions
from app.models.user import User
from app.schemas.assumptions import FinancialAssumptionsResponse, FinancialAssumptionsUpdate
from app.services import assumptions_service
from app.services.assumptions_service import DEFAULTS as _DEFAULTS

router = APIRouter(prefix="/assumptions", tags=["assumptions"])


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
        try:
            await db.flush()
        except IntegrityError:
            # Two concurrent first-access requests (e.g. Settings opened in
            # two tabs right after signup) can both pass the
            # scalar_one_or_none() check above before either commits — the
            # loser's insert violates financial_assumptions.user_id's unique
            # constraint. Recover by discarding this attempt and returning
            # the row the other request just created, rather than
            # propagating an unhandled error (Milestone1Implementation
            # Specification_FINAL.md §9).
            await db.rollback()
            result = await db.execute(
                select(FinancialAssumptions).where(
                    FinancialAssumptions.user_id == current_user.id
                )
            )
            assumptions = result.scalar_one()
        else:
            await db.refresh(assumptions)
            await db.commit()
    return assumptions


@router.put("", response_model=FinancialAssumptionsResponse)
async def upsert_assumptions(
    body: FinancialAssumptionsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialAssumptions:
    # Reused by the Life Event Engine's Retirement handler — exactly one
    # implementation of "create-or-update assumptions", not two.
    assumptions, _before_state, _after_state = await assumptions_service.update_assumptions_fields(
        db, current_user, body.model_dump(exclude_unset=True)
    )
    return assumptions
