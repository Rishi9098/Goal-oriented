"""Life Event Engine — Divorce (LifeEventEngineArchitecture.md §5.4).

Soft-deletes the spouse `HouseholdMember` and its cascading `Dependent`
via `family_service.remove_member` — extended (not duplicated) to accept
and deactivate the dependent alongside the member, exactly the same
mutation `DELETE /family/members/{id}` now performs too. No calculation
is touched. The two "review" notification prompts §5.4 calls for
(insurance coverage, nominee designations) are read-only, purely-live
checks added to `notification_service._collect_divorce_review_facts` —
no new stored fact, following the exact philosophy every other
notification source in this codebase already uses.
"""

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import family_service, life_event_service
from app.services.life_event_service import EntityEffect

_MEMBER_SNAPSHOT_FIELDS = ("relationship_type", "name", "is_active")
_DEPENDENT_SNAPSHOT_FIELDS = ("dependent_type", "date_of_birth", "gender", "is_active")


class DivorceHandler:
    """Required inputs: `member_id` — the spouse `HouseholdMember` to
    remove (the UI defaults this to the one active spouse; the handler
    itself accepts whichever id it's given, matching
    `DELETE /family/members/{id}`'s own lack of a relationship-type
    restriction beyond blocking "self")."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        member_id = uuid.UUID(inputs["member_id"])
        household, _created = await family_service.get_or_create_household(db, user)

        found = await family_service.get_member_and_dependent(db, household, member_id)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
            )
        member, dependent = found

        if member.relationship_type == "self":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the household creator",
            )

        member_before = life_event_service.snapshot(member, _MEMBER_SNAPSHOT_FIELDS)
        dependent_before = (
            life_event_service.snapshot(dependent, _DEPENDENT_SNAPSHOT_FIELDS)
            if dependent is not None
            else None
        )

        await family_service.remove_member(db, user, member, dependent)

        member_after = life_event_service.snapshot(member, _MEMBER_SNAPSHOT_FIELDS)
        effects = [
            EntityEffect(
                entity_table="household_members",
                entity_id=member.id,
                change_type="soft_delete",
                before_state=member_before,
                after_state=member_after,
            )
        ]
        if dependent is not None:
            dependent_after = life_event_service.snapshot(dependent, _DEPENDENT_SNAPSHOT_FIELDS)
            effects.append(
                EntityEffect(
                    entity_table="dependents",
                    entity_id=dependent.id,
                    change_type="soft_delete",
                    before_state=dependent_before,
                    after_state=dependent_after,
                )
            )

        return effects
