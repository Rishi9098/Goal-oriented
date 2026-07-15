"""Life Event Engine — New Loan (LifeEventEngineArchitecture.md §5.9).

Creates a Liability, with an optional linked Asset create (e.g. "what did
this loan fund?" — a car) for symmetry with House Purchase, never
mandatory. Both writes go through functions the corresponding
`POST /financials/liabilities` and `POST /financials/assets` endpoints
already call (`financials_service.create_liability`,
`financials_service.create_asset`) — no calculation is duplicated here.
`family_recommendations_service`'s `high_interest_debt` rule reads
liabilities live, so it reflects a high-rate new loan on the very next
read with no new logic in this handler.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import AssetCreate, LiabilityCreate
from app.services import financials_service
from app.services.life_event_service import EntityEffect


class NewLoanHandler:
    """Required inputs: `liability_type`, `balance`, `monthly_payment`.
    Optional: `interest_rate`, `institution`, `description`. Optional
    linked purchase, explicit opt-in only: `asset_type` + `asset_value`
    together create the funded Asset (e.g. the car this loan paid for);
    either alone is a no-op for the asset, matching Salary Raise's
    "never assume an optional step" rule."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        raw_interest_rate = inputs.get("interest_rate")
        liability, liability_after = await financials_service.create_liability(
            db,
            user,
            LiabilityCreate(
                liability_type=inputs["liability_type"],
                institution=inputs.get("institution"),
                description=inputs.get("description"),
                balance=float(inputs["balance"]),
                interest_rate=float(raw_interest_rate) if raw_interest_rate is not None else None,
                monthly_payment=float(inputs.get("monthly_payment", 0.0)),
            ),
        )
        effects = [
            EntityEffect(
                entity_table="liabilities",
                entity_id=liability.id,
                change_type="create",
                before_state=None,
                after_state=liability_after,
            )
        ]

        asset_type = inputs.get("asset_type")
        asset_value = inputs.get("asset_value")
        if asset_type is not None and asset_value is not None:
            asset, asset_after = await financials_service.create_asset(
                db,
                user,
                AssetCreate(
                    asset_type=asset_type,
                    institution=inputs.get("asset_institution"),
                    description=inputs.get("asset_description", "Financed purchase"),
                    current_value=float(asset_value),
                ),
            )
            effects.append(
                EntityEffect(
                    entity_table="assets",
                    entity_id=asset.id,
                    change_type="create",
                    before_state=None,
                    after_state=asset_after,
                )
            )

        return effects
