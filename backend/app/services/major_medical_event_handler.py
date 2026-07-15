"""Life Event Engine — Major Medical Event (LifeEventEngineArchitecture.md §5.13).

Creates a new healthcare expense or increases an existing one, with two
independent optional steps: reducing a liquid asset for a lump-sum
payment, and financing the rest with a new liability. Every write goes
through a function an existing endpoint or a prior event's own
extraction already provides (`financials_service.create_expense`/
`update_expense`, `adjust_asset_value` — reused unmodified from House
Purchase/Home Sale, `create_liability` — reused unmodified from New
Loan) — no calculation is duplicated here.

Entities NOT changed, with the architecture's own honest reason why: the
`Expense` model has no "one-time" flag — `monthly_amount` is inherently
recurring. This handler does not invent a one-time-expense concept the
schema doesn't support; the "this is an ongoing expense until you edit
it" notice is a UI-only confirmation-screen concern, not a write this
handler performs.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import ExpenseCreate, ExpenseUpdate, LiabilityCreate
from app.services import financials_service
from app.services.life_event_service import EntityEffect


class MajorMedicalEventHandler:
    """Required inputs: `monthly_amount`. Either `expense_id` (increases
    an existing healthcare expense) or, if absent, a new one is created.
    Optional lump-sum payment, explicit opt-in only: `lump_sum_asset_id`
    + `lump_sum_amount` together reduce an existing liquid asset.
    Optional financing, explicit opt-in only: `loan_balance` (+
    `loan_interest_rate`, `loan_monthly_payment`) creates a new
    liability."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        monthly_amount = float(inputs["monthly_amount"])
        expense_id = inputs.get("expense_id")

        if expense_id is not None:
            expense, expense_before, expense_after = await financials_service.update_expense(
                db, user, uuid.UUID(expense_id), ExpenseUpdate(monthly_amount=monthly_amount)
            )
            expense_effect = EntityEffect(
                entity_table="expenses",
                entity_id=expense.id,
                change_type="update",
                before_state=expense_before,
                after_state=expense_after,
            )
        else:
            expense, expense_after = await financials_service.create_expense(
                db,
                user,
                ExpenseCreate(
                    category="healthcare",
                    description=inputs.get("description", "Medical expense"),
                    monthly_amount=monthly_amount,
                ),
            )
            expense_effect = EntityEffect(
                entity_table="expenses",
                entity_id=expense.id,
                change_type="create",
                before_state=None,
                after_state=expense_after,
            )
        effects = [expense_effect]

        lump_sum_asset_id = inputs.get("lump_sum_asset_id")
        lump_sum_amount = inputs.get("lump_sum_amount")
        if lump_sum_asset_id is not None and lump_sum_amount is not None:
            funding_asset, funding_before, funding_after = (
                await financials_service.adjust_asset_value(
                    db, user, uuid.UUID(lump_sum_asset_id), -float(lump_sum_amount)
                )
            )
            effects.append(
                EntityEffect(
                    entity_table="assets",
                    entity_id=funding_asset.id,
                    change_type="update",
                    before_state=funding_before,
                    after_state=funding_after,
                )
            )

        loan_balance = inputs.get("loan_balance")
        if loan_balance is not None:
            raw_interest_rate = inputs.get("loan_interest_rate")
            liability, liability_after = await financials_service.create_liability(
                db,
                user,
                LiabilityCreate(
                    liability_type="personal_loan",
                    description=inputs.get("loan_description", "Medical financing"),
                    balance=float(loan_balance),
                    interest_rate=(
                        float(raw_interest_rate) if raw_interest_rate is not None else None
                    ),
                    monthly_payment=float(inputs.get("loan_monthly_payment", 0.0)),
                ),
            )
            effects.append(
                EntityEffect(
                    entity_table="liabilities",
                    entity_id=liability.id,
                    change_type="create",
                    before_state=None,
                    after_state=liability_after,
                )
            )

        return effects
