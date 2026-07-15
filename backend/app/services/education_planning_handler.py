"""Life Event Engine — Education Planning.

Not one of `LifeEventEngineArchitecture.md`'s original 15 catalogued
events — added to this run's ordered list. A pure goal-creation event:
creates a `Goal` with `category="education"` via
`planning_service.create_goal`, the exact path `POST /goals` and Birth of
Child's own optional education-goal sub-step already use. No new entity,
no new calculation trigger — the goal's `probability` is computed by the
same unconditional-on-create Monte Carlo run every goal creation already
gets.
"""

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.goal import GoalCreate
from app.services import planning_service
from app.services.life_event_service import EntityEffect


class EducationPlanningHandler:
    """Required inputs: `name`, `target_amount`, `target_date` (ISO date
    string). Optional: `current_amount` (default 0.0),
    `monthly_contribution` (default 0.0), `risk_profile` (default
    "balanced")."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        goal, after_state = await planning_service.create_goal(
            db,
            user,
            GoalCreate(
                name=inputs["name"],
                category="education",
                target_amount=float(inputs["target_amount"]),
                current_amount=float(inputs.get("current_amount", 0.0)),
                target_date=date.fromisoformat(inputs["target_date"]),
                monthly_contribution=float(inputs.get("monthly_contribution", 0.0)),
                risk_profile=inputs.get("risk_profile", "balanced"),
            ),
        )
        return [
            EntityEffect(
                entity_table="goals",
                entity_id=goal.id,
                change_type="create",
                before_state=None,
                after_state=after_state,
            )
        ]
