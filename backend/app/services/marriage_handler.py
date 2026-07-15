"""Life Event Engine — Marriage (LifeEventEngineArchitecture.md §5.3).

Creates the spouse `HouseholdMember` (`relationship_type="spouse"`) and
its cascading `Dependent` row via the exact function
`routers/family.py`'s add-member endpoint already calls
(`family_service.create_member`) — its existing validation
(`validate_member_fields`) is reused unmodified, not re-implemented. No
Monte Carlo/calculation logic is touched: marriage alone moves no money.

Notifications are free: `create_member` already writes a
`family_member_added` AuditLog row, which `notification_service`'s
pre-existing `_collect_family_member_added_facts` collector already turns
into a notification. `notification_service._LIFE_EVENT_SKIP_TYPES`
excludes `"marriage"` from the newer, generic `_collect_life_event_facts`
collector specifically to prevent this event producing two notifications
for one real-world action — see that constant's own docstring.
"""

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.family import FamilyMemberCreate
from app.services import family_service, life_event_service
from app.services.life_event_service import EntityEffect

_MEMBER_SNAPSHOT_FIELDS = ("relationship_type", "name", "is_active")
_DEPENDENT_SNAPSHOT_FIELDS = ("dependent_type", "date_of_birth", "gender", "is_active")


class MarriageHandler:
    """Required inputs: `name`, `date_of_birth` (ISO date string —
    `validate_member_fields` requires a date of birth for
    relationship_type="spouse"; that existing validation is reused
    unmodified here, even though §5.3 itself describes date of birth as
    optional). Optional: `gender`, `relationship_detail`."""

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
                    relationship_type="spouse",
                    name=inputs["name"],
                    date_of_birth=(
                        date.fromisoformat(raw_date_of_birth)
                        if raw_date_of_birth is not None
                        else None
                    ),
                    gender=inputs.get("gender"),
                    relationship_detail=inputs.get("relationship_detail"),
                ),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

        member_after = life_event_service.snapshot(member, _MEMBER_SNAPSHOT_FIELDS)
        dependent_after = life_event_service.snapshot(dependent, _DEPENDENT_SNAPSHOT_FIELDS)

        return [
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
