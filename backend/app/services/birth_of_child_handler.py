"""Life Event Engine — Birth of Child (LifeEventEngineArchitecture.md §5.5).

Creates the child `HouseholdMember` (`relationship_type="child"`) and its
cascading `Dependent` (`dependent_type="minor_child"`,
`is_tax_dependent=True` by default) via `family_service.create_member`
unmodified — the same reuse this event shares with Marriage. Optionally
also creates an education-category `Goal` ("start a college fund?") via
`planning_service.create_goal`, the exact path `POST /goals` already
uses, so its unconditional Monte Carlo run on create is the same trigger
that path already has, not a new one.

Notifications are free via the same mechanism as Marriage:
`notification_service._LIFE_EVENT_SKIP_TYPES` also excludes
`"birth_of_child"` to avoid the identical duplicate-notification
collision Marriage's own implementation found and fixed.

Also registered under the `"adoption"` event_type (see `main.py`'s
`_register_life_event_handlers`) — LifeEventEngineArchitecture.md §5.6
states Adoption is "identical to Birth of Child in every respect" for
entities changed, calculations, recommendations, notifications, undo,
and audit; the only distinction is which string `life_events.event_type`
records, for history and reporting. The schema has no field
distinguishing "born into" from "adopted into" a family, and this design
does not invent one speculatively (§5.6's own "honest schema note").
Since this class has no event-type-specific literal anywhere in its
body, registering it twice — not a second, near-duplicate handler file —
is the correct, minimal way to satisfy "identical in every respect."
"""

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.family import FamilyMemberCreate
from app.schemas.goal import GoalCreate
from app.services import family_service, life_event_service, planning_service
from app.services.life_event_service import EntityEffect

_MEMBER_SNAPSHOT_FIELDS = ("relationship_type", "name", "is_active")
_DEPENDENT_SNAPSHOT_FIELDS = ("dependent_type", "date_of_birth", "gender", "is_active")


class BirthOfChildHandler:
    """Required inputs: `name`, `date_of_birth` (ISO date string —
    required for relationship_type="child", same rule Marriage reuses for
    "spouse"). Optional: `gender`. Optional linked goal, explicit opt-in
    only: `goal_target_amount` + `goal_target_date` (ISO date string)
    together create the education fund; either alone is a no-op for the
    goal."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        household, _created = await family_service.get_or_create_household(db, user)
        raw_date_of_birth = inputs.get("date_of_birth")

        try:
            member, dependent = await family_service.create_member(
                db,
                user,
                household,
                FamilyMemberCreate(
                    relationship_type="child",
                    name=inputs["name"],
                    date_of_birth=(
                        date.fromisoformat(raw_date_of_birth)
                        if raw_date_of_birth is not None
                        else None
                    ),
                    gender=inputs.get("gender"),
                    is_tax_dependent=True,
                ),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

        member_after = life_event_service.snapshot(member, _MEMBER_SNAPSHOT_FIELDS)
        dependent_after = life_event_service.snapshot(dependent, _DEPENDENT_SNAPSHOT_FIELDS)

        effects = [
            EntityEffect(
                entity_table="household_members",
                entity_id=member.id,
                change_type="create",
                before_state=None,
                after_state=member_after,
            ),
            EntityEffect(
                entity_table="dependents",
                entity_id=dependent.id,
                change_type="create",
                before_state=None,
                after_state=dependent_after,
            ),
        ]

        goal_target_amount = inputs.get("goal_target_amount")
        goal_target_date = inputs.get("goal_target_date")
        if goal_target_amount is not None and goal_target_date is not None:
            goal, goal_after = await planning_service.create_goal(
                db,
                user,
                GoalCreate(
                    name=inputs.get("goal_name", f"{inputs['name']}'s College Fund"),
                    category="education",
                    target_amount=float(goal_target_amount),
                    current_amount=float(inputs.get("goal_current_amount", 0.0)),
                    target_date=date.fromisoformat(goal_target_date),
                    monthly_contribution=float(inputs.get("goal_monthly_contribution", 0.0)),
                    risk_profile=inputs.get("goal_risk_profile", "balanced"),
                ),
            )
            effects.append(
                EntityEffect(
                    entity_table="goals",
                    entity_id=goal.id,
                    change_type="create",
                    before_state=None,
                    after_state=goal_after,
                )
            )

        return effects
