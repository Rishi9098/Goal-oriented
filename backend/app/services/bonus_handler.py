"""Life Event Engine — Bonus.

Not one of `LifeEventEngineArchitecture.md`'s original 15 catalogued
events — added to this run's ordered list. Modeled directly on Inheritance
(§5.11), which this event's shape matches exactly: a one-time cash
windfall that creates a liquid `Asset`, with no `IncomeSource` (a bonus is
not ongoing income, the same distinction §5.11 draws for an inherited
asset's optional rental income). Inheritance itself is pure-create — no
"add to an existing asset" step — so Bonus follows that same shape rather
than inventing a merge-into-existing-balance mutation this event doesn't
need.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import AssetCreate
from app.services import financials_service
from app.services.life_event_service import EntityEffect


class BonusHandler:
    """Required inputs: `amount`. Optional: `asset_type` (defaults to
    "savings" — one of `planning_service._LIQUID_ASSET_TYPES`, so the
    bonus counts as liquid for the `low_liquidity` recommendation
    immediately, matching how a real bonus payout lands in a bank
    account), `institution`, `description`."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        asset, after_state = await financials_service.create_asset(
            db,
            user,
            AssetCreate(
                asset_type=inputs.get("asset_type", "savings"),
                institution=inputs.get("institution"),
                description=inputs.get("description", "Bonus"),
                current_value=float(inputs["amount"]),
            ),
        )
        return [
            EntityEffect(
                entity_table="assets",
                entity_id=asset.id,
                change_type="create",
                before_state=None,
                after_state=after_state,
            )
        ]
