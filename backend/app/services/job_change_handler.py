"""Life Event Engine — Job Change (LifeEventEngineArchitecture.md §5.2).

Updates the profile's employer/occupation, soft-deletes the prior income
source, and creates a new one for the replacement role — modeling a real
job change honestly (a new employer relationship, not a renamed old one)
and preserving the old row's history, per the architecture's own
reasoning. All three writes go through functions the corresponding
`PUT /profile`, `DELETE /financials/income/{id}`, and
`POST /financials/income` endpoints already call
(`profile_service.update_profile_fields`,
`financials_service.deactivate_income_source`,
`financials_service.create_income_source`) — no calculation or validation
is duplicated here.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import IncomeSourceCreate
from app.services import financials_service, profile_service
from app.services.life_event_service import EntityEffect


class JobChangeHandler:
    """Required inputs: `old_income_source_id`, `new_employer`,
    `new_occupation`, `new_annual_amount`. Optional: `new_source_type`
    (defaults to "salary") and `description` for the new income row."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        old_income_id = uuid.UUID(inputs["old_income_source_id"])

        profile, profile_before, profile_after = await profile_service.update_profile_fields(
            db,
            user,
            {"employer": inputs["new_employer"], "occupation": inputs["new_occupation"]},
        )
        old_income, old_before, old_after = await financials_service.deactivate_income_source(
            db, user, old_income_id
        )
        new_income, new_after = await financials_service.create_income_source(
            db,
            user,
            IncomeSourceCreate(
                source_type=inputs.get("new_source_type", "salary"),
                annual_amount=float(inputs["new_annual_amount"]),
                description=inputs.get("description"),
            ),
        )

        return [
            EntityEffect(
                entity_table="user_profiles",
                entity_id=profile.id,
                change_type="create" if profile_before is None else "update",
                before_state=profile_before,
                after_state=profile_after,
            ),
            EntityEffect(
                entity_table="income_sources",
                entity_id=old_income.id,
                change_type="soft_delete",
                before_state=old_before,
                after_state=old_after,
            ),
            EntityEffect(
                entity_table="income_sources",
                entity_id=new_income.id,
                change_type="create",
                before_state=None,
                after_state=new_after,
            ),
        ]
