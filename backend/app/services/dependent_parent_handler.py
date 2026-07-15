"""Life Event Engine — Dependent Parent.

Not one of `LifeEventEngineArchitecture.md`'s original 15 catalogued
events — added to this run's ordered list. Modeled directly on
Marriage/Birth of Child (§5.3/§5.5): `family_service.create_member`
already supports `relationship_type="parent"` -> `dependent_type=
"elderly_parent"` natively, so this handler is that exact path with
parent-specific required inputs, nothing new. `validate_member_fields`
requires `relationship_detail` ("mother"/"father") and
`has_own_insurance` for a parent — reused unmodified, not re-derived —
and does *not* require `date_of_birth` (unlike spouse/child), matching
real-world onboarding where an elderly parent's exact birth date is
often not on hand.

Notifications are free via the same mechanism as Marriage/Birth of
Child/Adoption: `notification_service._LIFE_EVENT_SKIP_TYPES` also
excludes `"dependent_parent"`.
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
_DEPENDENT_SNAPSHOT_FIELDS = (
    "dependent_type",
    "date_of_birth",
    "gender",
    "relationship_detail",
    "has_own_insurance",
    "is_active",
)


class DependentParentHandler:
    """Required inputs: `name`, `relationship_detail` ("mother" or
    "father"), `has_own_insurance` ("yes"/"no"/"not_sure") —
    `validate_member_fields` requires both for relationship_type="parent".
    Optional: `date_of_birth` (ISO date string), `gender`."""

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
                    relationship_type="parent",
                    name=inputs["name"],
                    date_of_birth=(
                        date.fromisoformat(raw_date_of_birth)
                        if raw_date_of_birth is not None
                        else None
                    ),
                    gender=inputs.get("gender"),
                    relationship_detail=inputs.get("relationship_detail"),
                    has_own_insurance=inputs.get("has_own_insurance"),
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
