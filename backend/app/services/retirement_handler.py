"""Life Event Engine — Retirement (LifeEventEngineArchitecture.md §5.12).

"The most structurally distinct event — a status transition rather than
a single transaction, touching Profile, Income, and Assumptions
together." Sets `user_profiles.employment_status = "retired"`,
deactivates the given salary income sources, and offers three
independent, explicit opt-in steps: creating a pension income source,
updating retirement-planning assumptions, and updating one or more
retirement goals' `monthly_contribution`. Every write goes through a
function an existing endpoint or a prior event's own extraction already
provides (`profile_service.update_profile_fields`,
`financials_service.deactivate_income_source`/`create_income_source`,
`assumptions_service.update_assumptions_fields`,
`planning_service.update_goal_fields`) — no calculation is duplicated
here, and `calculate_goal_probability` reruns only for a goal whose
`monthly_contribution` was explicitly changed, never a bespoke
"recompute every goal on retirement" pass.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import IncomeSourceCreate
from app.services import assumptions_service, financials_service, planning_service, profile_service
from app.services.life_event_service import EntityEffect


class RetirementHandler:
    """Required inputs: `income_source_ids` (list of active salary income
    source ids to deactivate — may be empty if the user's income is
    already fully non-salary). Optional, each independent and explicit
    opt-in: `pension_amount` (+ `pension_description`) creates a pension
    income source; `retirement_age` and/or `social_security_monthly`
    updates assumptions; `goal_contributions` (a list of
    `{"goal_id": ..., "new_monthly_contribution": ...}` dicts) updates
    one or more retirement goals."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        profile, profile_before, profile_after = await profile_service.update_profile_fields(
            db, user, {"employment_status": "retired"}
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

        for income_id in inputs.get("income_source_ids", []):
            income, income_before, income_after = (
                await financials_service.deactivate_income_source(
                    db, user, uuid.UUID(income_id)
                )
            )
            effects.append(
                EntityEffect(
                    entity_table="income_sources",
                    entity_id=income.id,
                    change_type="soft_delete",
                    before_state=income_before,
                    after_state=income_after,
                )
            )

        pension_amount = inputs.get("pension_amount")
        if pension_amount is not None:
            pension, pension_after = await financials_service.create_income_source(
                db,
                user,
                IncomeSourceCreate(
                    source_type="pension",
                    annual_amount=float(pension_amount),
                    description=inputs.get("pension_description", "Pension"),
                ),
            )
            effects.append(
                EntityEffect(
                    entity_table="income_sources",
                    entity_id=pension.id,
                    change_type="create",
                    before_state=None,
                    after_state=pension_after,
                )
            )

        assumptions_updates: dict[str, Any] = {}
        if inputs.get("retirement_age") is not None:
            assumptions_updates["retirement_age"] = int(inputs["retirement_age"])
        if inputs.get("social_security_monthly") is not None:
            assumptions_updates["social_security_monthly"] = float(
                inputs["social_security_monthly"]
            )
        if assumptions_updates:
            assumptions, assumptions_before, assumptions_after = (
                await assumptions_service.update_assumptions_fields(
                    db, user, assumptions_updates
                )
            )
            effects.append(
                EntityEffect(
                    entity_table="financial_assumptions",
                    entity_id=assumptions.id,
                    change_type="create" if assumptions_before is None else "update",
                    before_state=assumptions_before,
                    after_state=assumptions_after,
                )
            )

        for goal_update in inputs.get("goal_contributions", []):
            goal, goal_before, goal_after = await planning_service.update_goal_fields(
                db,
                user,
                uuid.UUID(goal_update["goal_id"]),
                {"monthly_contribution": float(goal_update["new_monthly_contribution"])},
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
