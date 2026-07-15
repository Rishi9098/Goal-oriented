"""Life Event Engine — House Purchase (LifeEventEngineArchitecture.md §5.7).

Creates the home `Asset` (`asset_type="real_estate"`) and the mortgage
`Liability`, with two independent optional steps: reducing an existing
liquid asset for the down payment, and bumping a linked "Home Purchase"
goal's `current_amount` (in `CALCULATION_CONTEXT_FIELDS`, so
`calculate_goal_probability` reruns for it via the same trigger
`PATCH /goals/{id}` already uses). All four possible writes go through
functions the corresponding endpoints/extractions already provide
(`financials_service.create_asset`, `create_liability`,
`adjust_asset_value`, `planning_service.update_goal_fields`) — no
calculation is duplicated here.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import AssetCreate, LiabilityCreate
from app.services import financials_service, planning_service
from app.services.life_event_service import EntityEffect


class HousePurchaseHandler:
    """Required inputs: `property_value`, `mortgage_balance`. Optional
    mortgage terms: `mortgage_interest_rate`, `mortgage_monthly_payment`,
    `mortgage_institution`. Two independent optional steps, each
    explicit-opt-in (both fields of a pair must be present):
    `down_payment_asset_id` + `down_payment_amount` reduces an existing
    liquid asset; `goal_id` + `new_goal_current_amount` bumps a linked
    goal's progress."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        asset, asset_after = await financials_service.create_asset(
            db,
            user,
            AssetCreate(
                asset_type="real_estate",
                institution=inputs.get("institution"),
                description=inputs.get("description", "Home"),
                current_value=float(inputs["property_value"]),
            ),
        )
        effects = [
            EntityEffect(
                entity_table="assets",
                entity_id=asset.id,
                change_type="create",
                before_state=None,
                after_state=asset_after,
            )
        ]

        raw_interest_rate = inputs.get("mortgage_interest_rate")
        liability, liability_after = await financials_service.create_liability(
            db,
            user,
            LiabilityCreate(
                liability_type="mortgage",
                institution=inputs.get("mortgage_institution"),
                description=inputs.get("mortgage_description", "Mortgage"),
                balance=float(inputs["mortgage_balance"]),
                interest_rate=float(raw_interest_rate) if raw_interest_rate is not None else None,
                monthly_payment=float(inputs.get("mortgage_monthly_payment", 0.0)),
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

        down_payment_asset_id = inputs.get("down_payment_asset_id")
        down_payment_amount = inputs.get("down_payment_amount")
        if down_payment_asset_id is not None and down_payment_amount is not None:
            funding_asset, funding_before, funding_after = (
                await financials_service.adjust_asset_value(
                    db, user, uuid.UUID(down_payment_asset_id), -float(down_payment_amount)
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

        goal_id = inputs.get("goal_id")
        new_goal_current_amount = inputs.get("new_goal_current_amount")
        if goal_id is not None and new_goal_current_amount is not None:
            goal, goal_before, goal_after = await planning_service.update_goal_fields(
                db,
                user,
                uuid.UUID(goal_id),
                {"current_amount": float(new_goal_current_amount)},
            )
            effects.append(
                EntityEffect(
                    entity_table="goals",
                    entity_id=goal.id,
                    change_type="update",
                    before_state=goal_before,
                    after_state=goal_after,
                )
            )

        return effects
