"""Life Event Engine — Adoption (LifeEventEngineArchitecture.md §5.6).

"Identical to Birth of Child in every respect" per the architecture — no
new handler class exists for this event; `BirthOfChildHandler` is
registered a second time under the `"adoption"` event_type (see
`main.py`). These tests confirm that registration actually works end to
end and that the recorded `life_events.event_type` is the one
observable difference, not a second copy of the handler's behavior.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.household import Dependent, HouseholdMember
from app.models.user import User
from app.services import life_event_service


class TestAdoptionSharesTheBirthOfChildHandler:
    async def test_adoption_is_registered_to_the_same_handler_class(self):
        assert "adoption" in life_event_service.registered_event_types()
        assert "birth_of_child" in life_event_service.registered_event_types()

    async def test_recording_an_adoption_creates_child_member_and_dependent(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="adoption",
            occurred_on=date(2026, 6, 1),
            inputs={"name": "Avery", "date_of_birth": "2020-01-15"},
        )

        assert life_event.event_type == "adoption"  # the one distinguishing fact
        assert life_event.status == "applied"
        assert len(life_event.effects) == 2
        assert life_event.effects[0].entity_table == "household_members"
        assert life_event.effects[1].entity_table == "dependents"

        result = await db.execute(
            select(HouseholdMember).where(HouseholdMember.id == life_event.effects[0].entity_id)
        )
        member = result.scalar_one()
        assert member.relationship_type == "child"

        result = await db.execute(
            select(Dependent).where(Dependent.id == life_event.effects[1].entity_id)
        )
        dependent = result.scalar_one()
        assert dependent.dependent_type == "minor_child"
        assert dependent.is_tax_dependent is True

    async def test_recording_an_adoption_also_supports_the_linked_education_goal(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="adoption",
            occurred_on=date.today(),
            inputs={
                "name": "Avery",
                "date_of_birth": "2020-01-15",
                "goal_target_amount": 60_000.0,
                "goal_target_date": (date.today() + timedelta(days=365 * 16)).isoformat(),
            },
        )

        assert len(life_event.effects) == 3
        assert life_event.effects[2].entity_table == "goals"

    async def test_writes_both_the_family_member_added_and_life_event_recorded_audit_rows(
        self, db: AsyncSession, user: User
    ):
        await life_event_service.record_life_event(
            db,
            user,
            event_type="adoption",
            occurred_on=date.today(),
            inputs={"name": "Avery", "date_of_birth": "2020-01-15"},
        )

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id,
                AuditLog.action.in_(["family_member_added", "life_event_recorded"]),
            )
        )
        rows = result.scalars().all()
        actions = {row.action for row in rows}
        assert actions == {"family_member_added", "life_event_recorded"}
        recorded_row = next(r for r in rows if r.action == "life_event_recorded")
        assert recorded_row.after_state["event_type"] == "adoption"  # not "birth_of_child"

    async def test_undo_soft_deletes_member_and_dependent(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="adoption",
            occurred_on=date.today(),
            inputs={"name": "Avery", "date_of_birth": "2020-01-15"},
        )
        member_id = life_event.effects[0].entity_id
        dependent_id = life_event.effects[1].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        member = await db.get(HouseholdMember, member_id)
        dependent = await db.get(Dependent, dependent_id)
        assert member is not None and member.is_active is False
        assert dependent is not None and dependent.is_active is False

    async def test_cannot_undo_another_users_adoption(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="adoption",
            occurred_on=date.today(),
            inputs={"name": "Avery", "date_of_birth": "2020-01-15"},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


class TestAdoptionNotificationDoesNotDuplicate:
    async def test_exactly_one_notification_appears_for_an_adoption_event(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        await life_event_service.record_life_event(
            db,
            user,
            event_type="adoption",
            occurred_on=date.today(),
            inputs={"name": "Avery", "date_of_birth": "2020-01-15"},
        )
        await db.commit()

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]

        life_event_items = [i for i in items if i["source"] == "life_event"]
        family_items = [i for i in items if i["source"] == "family_member_added"]
        assert life_event_items == []
        assert len(family_items) == 1
