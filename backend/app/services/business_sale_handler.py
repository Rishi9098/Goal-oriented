"""Life Event Engine — Business Sale (LifeEventEngineArchitecture.md §5.15).

Directs sale proceeds to a liquid Asset (existing or new — mirroring Home
Sale's own proceeds-destination shape exactly), with three further
independent optional steps: paying off a business Liability, creating an
ongoing installment-payout IncomeSource, and reverting
`employment_status` (e.g. back to "employed"/"retired" if the business
was the sole income source). Every write goes through a function a prior
event's own extraction already provides
(`financials_service.adjust_asset_value`/`create_asset` — Home Sale/
Bonus, `close_liability` — Loan Payoff/Home Sale, `create_income_source`
— Job Change/Retirement/Inheritance, `profile_service.
update_profile_fields` — Job Change/Retirement/Business Start) — this
event, like Business Start and Adoption before it, needed zero new
service-layer code.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import AssetCreate, IncomeSourceCreate
from app.services import financials_service, profile_service
from app.services.life_event_service import EntityEffect


class BusinessSaleHandler:
    """Required inputs: `net_proceeds`. Proceeds destination:
    `proceeds_asset_id` adds to an existing liquid asset; if absent, a
    new one is created with `proceeds_asset_type` (defaults to
    "savings"). Three further independent optional steps, each explicit
    opt-in: `business_liability_id` pays off a business liability;
    `income_amount` creates an ongoing installment-payout IncomeSource
    (`source_type="other"`); `new_employment_status` reverts the
    profile's employment status."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        net_proceeds = float(inputs["net_proceeds"])
        proceeds_asset_id = inputs.get("proceeds_asset_id")

        if proceeds_asset_id is not None:
            asset, asset_before, asset_after = await financials_service.adjust_asset_value(
                db, user, uuid.UUID(proceeds_asset_id), net_proceeds
            )
            effects = [
                EntityEffect(
                    entity_table="assets",
                    entity_id=asset.id,
                    change_type="update",
                    before_state=asset_before,
                    after_state=asset_after,
                )
            ]
        else:
            asset, asset_after = await financials_service.create_asset(
                db,
                user,
                AssetCreate(
                    asset_type=inputs.get("proceeds_asset_type", "savings"),
                    description=inputs.get("proceeds_description", "Business sale proceeds"),
                    current_value=net_proceeds,
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

        business_liability_id = inputs.get("business_liability_id")
        if business_liability_id is not None:
            liability, liability_before, liability_after = (
                await financials_service.close_liability(
                    db, user, uuid.UUID(business_liability_id)
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

        income_amount = inputs.get("income_amount")
        if income_amount is not None:
            income, income_after = await financials_service.create_income_source(
                db,
                user,
                IncomeSourceCreate(
                    source_type="other",
                    annual_amount=float(income_amount),
                    description=inputs.get("income_description", "Business sale payout"),
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

        new_employment_status = inputs.get("new_employment_status")
        if new_employment_status is not None:
            profile, profile_before, profile_after = (
                await profile_service.update_profile_fields(
                    db, user, {"employment_status": new_employment_status}
                )
            )
            effects.append(
                EntityEffect(
                    entity_table="user_profiles",
                    entity_id=profile.id,
                    change_type="create" if profile_before is None else "update",
                    before_state=profile_before,
                    after_state=profile_after,
                )
            )

        return effects
