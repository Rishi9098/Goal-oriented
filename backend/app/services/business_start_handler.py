"""Life Event Engine — Business Start (LifeEventEngineArchitecture.md §5.14).

Sets `user_profiles.employment_status = "self_employed"`, with two
independent optional steps: startup costs paid from savings (reduces a
liquid asset) or ongoing (creates an Expense), and startup debt (creates
a Liability). Every write goes through a function a prior event's own
extraction already provides (`profile_service.update_profile_fields`,
`financials_service.adjust_asset_value`, `create_expense`,
`create_liability`) — this event needed zero new service-layer code.

**No `income_sources` row is created here** — a business start commonly
precedes any revenue, and a $0 income row would misrepresent the
household's actual finances; income is recorded later via ordinary
Financials editing or a future life event once revenue is real.

**Honest schema gap, not silently worked around**: `liabilities.
liability_type` has no dedicated `business_loan` value yet. A business
loan is recorded as `"other"`, with the specific label carried in
`description` — named here explicitly as a known, deliberate placeholder
per the architecture's own note, not a bug.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import ExpenseCreate, LiabilityCreate
from app.services import financials_service, profile_service
from app.services.life_event_service import EntityEffect


class BusinessStartHandler:
    """No required inputs beyond the event itself. Optional, independent
    steps, each explicit opt-in: `funding_asset_id` + `funding_amount`
    reduces an existing liquid asset for a one-time startup cost;
    `ongoing_expense_amount` creates a recurring business Expense;
    `loan_balance` creates a startup-debt Liability
    (`liability_type="other"` — see this module's own docstring)."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        profile, profile_before, profile_after = await profile_service.update_profile_fields(
            db, user, {"employment_status": "self_employed"}
        )
        effects = [
            EntityEffect(
                entity_table="user_profiles",
                entity_id=profile.id,
                change_type="create" if profile_before is None else "update",
                before_state=profile_before,
                after_state=profile_after,
            )
        ]

        funding_asset_id = inputs.get("funding_asset_id")
        funding_amount = inputs.get("funding_amount")
        if funding_asset_id is not None and funding_amount is not None:
            asset, asset_before, asset_after = await financials_service.adjust_asset_value(
                db, user, uuid.UUID(funding_asset_id), -float(funding_amount)
            )
            effects.append(
                EntityEffect(
                    entity_table="assets",
                    entity_id=asset.id,
                    change_type="update",
                    before_state=asset_before,
                    after_state=asset_after,
                )
            )

        ongoing_expense_amount = inputs.get("ongoing_expense_amount")
        if ongoing_expense_amount is not None:
            expense, expense_after = await financials_service.create_expense(
                db,
                user,
                ExpenseCreate(
                    category="business",
                    description=inputs.get("expense_description", "Business startup cost"),
                    monthly_amount=float(ongoing_expense_amount),
                ),
            )
            effects.append(
                EntityEffect(
                    entity_table="expenses",
                    entity_id=expense.id,
                    change_type="create",
                    before_state=None,
                    after_state=expense_after,
                )
            )

        loan_balance = inputs.get("loan_balance")
        if loan_balance is not None:
            raw_interest_rate = inputs.get("loan_interest_rate")
            liability, liability_after = await financials_service.create_liability(
                db,
                user,
                LiabilityCreate(
                    liability_type="other",
                    description=inputs.get("loan_description", "Business loan"),
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
