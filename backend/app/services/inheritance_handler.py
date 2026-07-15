"""Life Event Engine — Inheritance (LifeEventEngineArchitecture.md §5.11).

Creates an Asset for the inherited cash/investment/property, with an
optional linked IncomeSource create ("does this generate ongoing
income?" — e.g. an inherited rental property), never mandatory. Both
writes go through functions the corresponding endpoints/extractions
already provide (`financials_service.create_asset`, `create_income_source`
— both reused unmodified from Bonus and Job Change respectively) — no
calculation is duplicated here. `family_recommendations_service`'s
`negative_net_worth_trend`/`low_liquidity` rules read assets live, so
they reflect the inheritance on the very next read with no new logic in
this handler.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import AssetCreate, IncomeSourceCreate
from app.services import financials_service
from app.services.life_event_service import EntityEffect


class InheritanceHandler:
    """Required inputs: `amount`. Optional: `asset_type` (defaults to
    "savings" — inherited cash is assumed liquid unless told otherwise),
    `institution`, `description`. Optional linked income, explicit
    opt-in only: `income_amount` creates the ongoing IncomeSource
    (`income_source_type` defaults to "rental", per the architecture's
    own flagship example of an inherited rental property)."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        asset, asset_after = await financials_service.create_asset(
            db,
            user,
            AssetCreate(
                asset_type=inputs.get("asset_type", "savings"),
                institution=inputs.get("institution"),
                description=inputs.get("description", "Inheritance"),
                current_value=float(inputs["amount"]),
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

        income_amount = inputs.get("income_amount")
        if income_amount is not None:
            income, income_after = await financials_service.create_income_source(
                db,
                user,
                IncomeSourceCreate(
                    source_type=inputs.get("income_source_type", "rental"),
                    annual_amount=float(income_amount),
                    description=inputs.get("income_description", "Inherited income"),
                ),
            )
            effects.append(
                EntityEffect(
                    entity_table="income_sources",
                    entity_id=income.id,
                    change_type="create",
                    before_state=None,
                    after_state=income_after,
                )
            )

        return effects
