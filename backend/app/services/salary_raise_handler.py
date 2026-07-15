"""Life Event Engine — Salary Raise (LifeEventEngineArchitecture.md §5.1).

Updates an existing IncomeSource's annual_amount, with an optional linked
step that also bumps a goal's monthly_contribution. Computes nothing
itself: both writes go through the exact functions
`PATCH /financials/income/{id}` and `PATCH /goals/{id}` already call
(`financials_service.update_income_source`, `planning_service.
update_goal_fields`), so ADR-001's conditional Monte Carlo trigger fires
for the goal step exactly as it always has — this handler adds no second
copy of that check.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.financials import IncomeSourceUpdate
from app.services import financials_service, planning_service
from app.services.life_event_service import EntityEffect


class SalaryRaiseHandler:
    """Required inputs: `income_source_id`, `new_annual_amount`. Optional:
    `goal_id` + `new_monthly_contribution` — taken only if both are
    present, matching the architecture's "explicit opt-in, never assumed"
    rule for optional life-event sub-steps."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        income_id = uuid.UUID(inputs["income_source_id"])
        new_annual_amount = float(inputs["new_annual_amount"])

        income, before_state, after_state = await financials_service.update_income_source(
            db, user, income_id, IncomeSourceUpdate(annual_amount=new_annual_amount)
        )
        effects = [
            EntityEffect(
                entity_table="income_sources",
                entity_id=income.id,
                change_type="update",
                before_state=before_state,
                after_state=after_state,
            )
        ]

        goal_id = inputs.get("goal_id")
        new_monthly_contribution = inputs.get("new_monthly_contribution")
        if goal_id is not None and new_monthly_contribution is not None:
            goal, goal_before, goal_after = await planning_service.update_goal_fields(
                db,
                user,
                uuid.UUID(goal_id),
                {"monthly_contribution": float(new_monthly_contribution)},
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
