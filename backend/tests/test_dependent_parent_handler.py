"""Life Event Engine — Dependent Parent.

Not one of the architecture's original 15 catalogued events (see this
event's own module docstring: modeled directly on Marriage/Birth of
Child, reusing family_service.create_member's existing
relationship_type="parent" support). Covers the handler in isolation,
the full record/undo workflow through the generic engine, a rollback
proof, and the shared notification-collision fix.
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.household import Dependent, HouseholdMember
from app.models.user import User
from app.services import life_event_service
from app.services.dependent_parent_handler import DependentParentHandler
from app.services.life_event_service import EntityEffect

# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestDependentParentHandlerUnit:
    async def test_apply_creates_parent_member_and_dependent(
        self, db: AsyncSession, user: User
    ):
        effects = await DependentParentHandler().apply(
            db,
            user,
            {
                "name": "Margaret",
                "relationship_detail": "mother",
                "has_own_insurance": "no",
            },
        )

        assert len(effects) == 2
        member_effect, dependent_effect = effects
        assert isinstance(member_effect, EntityEffect)
        assert member_effect.entity_table == "household_members"
        assert member_effect.after_state["relationship_type"] == "parent"
        assert member_effect.after_state["name"] == "Margaret"

        assert dependent_effect.entity_table == "dependents"
        assert dependent_effect.after_state["dependent_type"] == "elderly_parent"
        assert dependent_effect.after_state["relationship_detail"] == "mother"
        assert dependent_effect.after_state["has_own_insurance"] == "no"
        # date_of_birth is not required for a parent, unlike spouse/child.
        assert dependent_effect.after_state["date_of_birth"] is None

        result = await db.execute(
            select(HouseholdMember).where(HouseholdMember.id == member_effect.entity_id)
        )
        member = result.scalar_one()
        assert member.is_active is True

    async def test_apply_accepts_an_optional_date_of_birth(
        self, db: AsyncSession, user: User
    ):
        effects = await DependentParentHandler().apply(
            db,
            user,
            {
                "name": "Robert",
                "relationship_detail": "father",
                "has_own_insurance": "yes",
                "date_of_birth": "1955-08-20",
            },
        )

        assert effects[1].after_state["date_of_birth"] == "1955-08-20"

    async def test_apply_raises_422_when_relationship_detail_is_missing(
        self, db: AsyncSession, user: User
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await DependentParentHandler().apply(
                db, user, {"name": "Margaret", "has_own_insurance": "no"}
            )
        assert exc_info.value.status_code == 422

    async def test_apply_raises_422_when_has_own_insurance_is_missing(
        self, db: AsyncSession, user: User
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await DependentParentHandler().apply(
                db, user, {"name": "Margaret", "relationship_detail": "mother"}
            )
        assert exc_info.value.status_code == 422


# ── Integration: the full workflow through the generic engine ──────────────


class TestDependentParentFullWorkflow:
    async def test_records_life_event_and_both_effects(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="dependent_parent",
            occurred_on=date(2026, 7, 1),
            inputs={
                "name": "Margaret",
                "relationship_detail": "mother",
                "has_own_insurance": "no",
            },
        )

        assert life_event.event_type == "dependent_parent"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 2

    async def test_writes_both_the_family_member_added_and_life_event_recorded_audit_rows(
        self, db: AsyncSession, user: User
    ):
        await life_event_service.record_life_event(
            db,
            user,
            event_type="dependent_parent",
            occurred_on=date.today(),
            inputs={
                "name": "Margaret",
                "relationship_detail": "mother",
                "has_own_insurance": "no",
            },
        )

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id,
                AuditLog.action.in_(["family_member_added", "life_event_recorded"]),
            )
        )
        actions = {row.action for row in result.scalars().all()}
        assert actions == {"family_member_added", "life_event_recorded"}


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _DependentParentThenFailHandler:
    def __init__(self) -> None:
        self._real = DependentParentHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the member/dependent writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        await db.commit()

        life_event_service.register_handler(
            "dependent_parent_then_fail", _DependentParentThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="dependent_parent_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "name": "Margaret",
                        "relationship_detail": "mother",
                        "has_own_insurance": "no",
                    },
                )

            await db.rollback()

            result = await db.execute(
                select(HouseholdMember).where(HouseholdMember.relationship_type == "parent")
            )
            assert result.scalars().all() == []
            result = await db.execute(
                select(Dependent).where(Dependent.dependent_type == "elderly_parent")
            )
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("dependent_parent_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_soft_deletes_member_and_dependent(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="dependent_parent",
            occurred_on=date.today(),
            inputs={
                "name": "Margaret",
                "relationship_detail": "mother",
                "has_own_insurance": "no",
            },
        )
        member_id = life_event.effects[0].entity_id
        dependent_id = life_event.effects[1].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        member = await db.get(HouseholdMember, member_id)
        dependent = await db.get(Dependent, dependent_id)
        assert member is not None and member.is_active is False
        assert dependent is not None and dependent.is_active is False

    async def test_cannot_undo_another_users_dependent_parent(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="dependent_parent",
            occurred_on=date.today(),
            inputs={
                "name": "Margaret",
                "relationship_detail": "mother",
                "has_own_insurance": "no",
            },
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Notification collision fix (shared with Marriage) ───────────────────────


class TestNotificationDoesNotDuplicate:
    async def test_exactly_one_notification_appears_for_a_dependent_parent_event(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        await life_event_service.record_life_event(
            db,
            user,
            event_type="dependent_parent",
            occurred_on=date.today(),
            inputs={
                "name": "Margaret",
                "relationship_detail": "mother",
                "has_own_insurance": "no",
            },
        )
        await db.commit()

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]

        life_event_items = [i for i in items if i["source"] == "life_event"]
        family_items = [i for i in items if i["source"] == "family_member_added"]
        assert life_event_items == []
        assert len(family_items) == 1
