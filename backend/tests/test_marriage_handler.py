"""Life Event Engine — Marriage (LifeEventEngineArchitecture.md §5.3).

Covers the handler in isolation, the full record/undo workflow through
the generic engine, a rollback proof, and the notification-collision fix
this event required (see notification_service._LIFE_EVENT_SKIP_TYPES) —
exactly one notification must appear per Marriage event, not two.
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.household import Dependent, HouseholdMember
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import life_event_service
from app.services.life_event_service import EntityEffect
from app.services.marriage_handler import MarriageHandler

# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestMarriageHandlerUnit:
    async def test_apply_creates_spouse_member_and_dependent(
        self, db: AsyncSession, user: User
    ):
        effects = await MarriageHandler().apply(
            db, user, {"name": "Jordan Lee", "date_of_birth": "1990-04-12"}
        )

        assert len(effects) == 2
        member_effect, dependent_effect = effects
        assert isinstance(member_effect, EntityEffect)
        assert member_effect.entity_table == "household_members"
        assert member_effect.change_type == "create"
        assert member_effect.before_state is None
        assert member_effect.after_state["relationship_type"] == "spouse"
        assert member_effect.after_state["name"] == "Jordan Lee"

        assert dependent_effect.entity_table == "dependents"
        assert dependent_effect.change_type == "create"
        assert dependent_effect.after_state["dependent_type"] == "spouse"
        assert dependent_effect.after_state["date_of_birth"] == "1990-04-12"

        result = await db.execute(
            select(HouseholdMember).where(HouseholdMember.id == member_effect.entity_id)
        )
        member = result.scalar_one()
        assert member.relationship_type == "spouse"
        assert member.is_active is True

    async def test_apply_raises_422_when_date_of_birth_is_missing(
        self, db: AsyncSession, user: User
    ):
        """Reuses family_service.validate_member_fields's own existing
        rule ("date_of_birth is required for relationship_type=spouse")
        rather than the handler inventing a second required-field check —
        the ValueError it raises is translated to the same 422 shape
        `POST /family/members` already uses."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await MarriageHandler().apply(db, user, {"name": "Jordan Lee"})
        assert exc_info.value.status_code == 422

    async def test_apply_creates_the_household_if_none_exists_yet(
        self, db: AsyncSession, user: User
    ):
        effects = await MarriageHandler().apply(
            db, user, {"name": "Sam Rivera", "date_of_birth": "1988-01-01"}
        )
        assert len(effects) == 2


# ── Integration: the full workflow through the generic engine ──────────────


class TestMarriageFullWorkflow:
    async def test_records_life_event_and_both_effects(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="marriage",
            occurred_on=date(2026, 5, 20),
            inputs={"name": "Jordan Lee", "date_of_birth": "1990-04-12"},
        )

        assert life_event.event_type == "marriage"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 2
        assert life_event.effects[0].entity_table == "household_members"
        assert life_event.effects[1].entity_table == "dependents"

    async def test_writes_both_the_family_member_added_and_life_event_recorded_audit_rows(
        self, db: AsyncSession, user: User
    ):
        """create_member's own pre-existing AuditLog write and the generic
        engine's are two separate, expected rows — this is what makes the
        notification free (see the module docstring)."""
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="marriage",
            occurred_on=date.today(),
            inputs={"name": "Jordan Lee", "date_of_birth": "1990-04-12"},
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
        assert recorded_row.after_state == {
            "life_event_id": str(life_event.id),
            "event_type": "marriage",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _MarriageThenFailHandler:
    def __init__(self) -> None:
        self._real = MarriageHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the member/dependent writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        user_id = user.id
        await db.commit()

        life_event_service.register_handler("marriage_then_fail", _MarriageThenFailHandler())
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="marriage_then_fail",
                    occurred_on=date.today(),
                    inputs={"name": "Jordan Lee", "date_of_birth": "1990-04-12"},
                )

            await db.rollback()

            result = await db.execute(
                select(HouseholdMember).where(HouseholdMember.relationship_type == "spouse")
            )
            assert result.scalars().all() == []
            result = await db.execute(select(Dependent).where(Dependent.dependent_type == "spouse"))
            assert result.scalars().all() == []

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("marriage_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_soft_deletes_member_and_dependent(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="marriage",
            occurred_on=date.today(),
            inputs={"name": "Jordan Lee", "date_of_birth": "1990-04-12"},
        )
        member_id = life_event.effects[0].entity_id
        dependent_id = life_event.effects[1].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False

        member = await db.get(HouseholdMember, member_id)
        dependent = await db.get(Dependent, dependent_id)
        assert member is not None and member.is_active is False
        assert dependent is not None and dependent.is_active is False

        await db.refresh(life_event)
        assert life_event.status == "undone"

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="marriage",
            occurred_on=date.today(),
            inputs={"name": "Jordan Lee", "date_of_birth": "1990-04-12"},
        )
        await life_event_service.undo_life_event(db, user, life_event.id)

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id, AuditLog.action == "life_event_undone"
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].after_state == {"life_event_id": str(life_event.id), "status": "undone"}

    async def test_undo_blocked_if_the_member_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="marriage",
            occurred_on=date.today(),
            inputs={"name": "Jordan Lee", "date_of_birth": "1990-04-12"},
        )
        member_id = life_event.effects[0].entity_id

        member = await db.get(HouseholdMember, member_id)
        assert member is not None
        member.name = "Changed Name"
        db.add(member)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert any(c.entity_table == "household_members" for c in result.conflicts)

    async def test_cannot_undo_another_users_marriage(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="marriage",
            occurred_on=date.today(),
            inputs={"name": "Jordan Lee", "date_of_birth": "1990-04-12"},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Notification collision fix ──────────────────────────────────────────────


class TestNotificationDoesNotDuplicate:
    async def test_exactly_one_notification_appears_for_a_marriage_event(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        """Regression test for the collision this event's implementation
        found: without notification_service._LIFE_EVENT_SKIP_TYPES
        excluding "marriage", both the pre-existing
        _collect_family_member_added_facts collector and the generic
        _collect_life_event_facts collector would fire for the same
        real-world action, producing two notifications instead of one."""
        await life_event_service.record_life_event(
            db,
            user,
            event_type="marriage",
            occurred_on=date.today(),
            inputs={"name": "Jordan Lee", "date_of_birth": "1990-04-12"},
        )
        await db.commit()

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]

        life_event_items = [i for i in items if i["source"] == "life_event"]
        family_items = [i for i in items if i["source"] == "family_member_added"]
        assert life_event_items == []
        assert len(family_items) == 1
