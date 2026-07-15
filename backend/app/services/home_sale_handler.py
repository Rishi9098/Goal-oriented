"""Life Event Engine — Home Sale (LifeEventEngineArchitecture.md §5.8).

Soft-deletes the home Asset, optionally soft-deletes the linked mortgage
Liability (if paid off by the sale — "defaults to yes if one exists"),
and directs net proceeds to a liquid Asset — either adding to an existing
one or creating a new one. Every write goes through a function an
existing endpoint or a prior event's own extraction already provides
(`financials_service.deactivate_asset`, `close_liability` — reused
unmodified from Loan Payoff, `adjust_asset_value`/`create_asset` — reused
unmodified from House Purchase/Bonus) — no calculation is duplicated
here.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import AssetCreate
from app.services import financials_service
from app.services.life_event_service import EntityEffect


class HomeSaleHandler:
    """Required inputs: `home_asset_id`, `net_proceeds`. Optional:
    `mortgage_liability_id` (soft-deleted too unless `payoff_mortgage` is
    explicitly `False` — "defaults to yes if one exists", per the
    architecture). Proceeds destination: `proceeds_asset_id` adds to an
    existing liquid asset; if absent, a new one is created with
    `proceeds_asset_type` (defaults to "savings")."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        home_asset_id = uuid.UUID(inputs["home_asset_id"])
        home_asset, home_before, home_after = await financials_service.deactivate_asset(
            db, user, home_asset_id
        )
        effects = [
            EntityEffect(
                entity_table="assets",
                entity_id=home_asset.id,
                change_type="soft_delete",
                before_state=home_before,
                after_state=home_after,
            )
        ]

        mortgage_liability_id = inputs.get("mortgage_liability_id")
        if mortgage_liability_id is not None and inputs.get("payoff_mortgage", True):
            liability, liability_before, liability_after = (
                await financials_service.close_liability(
                    db, user, uuid.UUID(mortgage_liability_id)
                )
            )
            effects.append(
                EntityEffect(
                    entity_table="liabilities",
                    entity_id=liability.id,
                    change_type="soft_delete",
                    before_state=liability_before,
                    after_state=liability_after,
                )
            )

        net_proceeds = float(inputs["net_proceeds"])
        proceeds_asset_id = inputs.get("proceeds_asset_id")
        if proceeds_asset_id is not None:
            proceeds_asset, proceeds_before, proceeds_after = (
                await financials_service.adjust_asset_value(
                    db, user, uuid.UUID(proceeds_asset_id), net_proceeds
                )
            )
            effects.append(
                EntityEffect(
                    entity_table="assets",
                    entity_id=proceeds_asset.id,
                    change_type="update",
                    before_state=proceeds_before,
                    after_state=proceeds_after,
                )
            )
        else:
            proceeds_asset, proceeds_after = await financials_service.create_asset(
                db,
                user,
                AssetCreate(
                    asset_type=inputs.get("proceeds_asset_type", "savings"),
                    description=inputs.get("proceeds_description", "Home sale proceeds"),
                    current_value=net_proceeds,
                ),
            )
            effects.append(
                EntityEffect(
                    entity_table="assets",
                    entity_id=proceeds_asset.id,
                    change_type="create",
                    before_state=None,
                    after_state=proceeds_after,
                )
            )

        return effects
