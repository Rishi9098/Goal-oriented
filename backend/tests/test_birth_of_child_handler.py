"""Life Event Engine — Birth of Child (LifeEventEngineArchitecture.md §5.5).

Covers the handler in isolation (member-only and member+education-goal
paths), the full record/undo workflow through the generic engine, a
rollback proof, and confirmation that the same notification-collision fix
Marriage required also applies here.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.goal import Goal
from app.models.household import Dependent, HouseholdMember
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import life_event_service
from app.services.birth_of_child_handler import BirthOfChildHandler
from app.services.life_event_service import EntityEffect

# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestBirthOfChildHandlerUnit:
    async def test_apply_creates_child_member_and_dependent_only(
        self, db: AsyncSession, user: User
    ):
        effects = await BirthOfChildHandler().apply(
            db, user, {"name": "Riley", "date_of_birth": "2026-03-01", "gender": "female"}
        )

        assert len(effects) == 2
        member_effect, dependent_effect = effects
        assert isinstance(member_effect, EntityEffect)
        assert member_effect.entity_table == "household_members"
        assert member_effect.after_state["relationship_type"] == "child"
        assert member_effect.after_state["name"] == "Riley"

        assert dependent_effect.entity_table == "dependents"
        assert dependent_effect.after_state["dependent_type"] == "minor_child"
        assert dependent_effect.after_state["gender"] == "female"

        result = await db.execute(
            select(Dependent).where(Dependent.id == dependent_effect.entity_id)
        )
        dependent = result.scalar_one()
        assert dependent.is_tax_dependent is True

    async def test_apply_also_creates_an_education_goal_when_both_fields_given(
        self, db: AsyncSession, user: User
    ):
        effects = await BirthOfChildHandler().apply(
            db,
            user,
            {
                "name": "Riley",
                "date_of_birth": "2026-03-01",
                "goal_target_amount": 80_000.0,
                "goal_target_date": (date.today() + timedelta(days=365 * 18)).isoformat(),
            },
        )

        assert len(effects) == 3
        goal_effect = effects[2]
        assert goal_effect.entity_table == "goals"
        assert goal_effect.change_type == "create"
        assert goal_effect.before_state is None
        assert goal_effect.after_state["target_amount"] == 80_000.0
        assert goal_effect.after_state["category"] == "education"
        assert "probability" in goal_effect.after_state

        result = await db.execute(select(Goal).where(Goal.id == goal_effect.entity_id))
        goal = result.scalar_one()
        assert goal.name == "Riley's College Fund"

    async def test_apply_ignores_goal_target_amount_without_a_target_date(
        self, db: AsyncSession, user: User
    ):
        effects = await BirthOfChildHandler().apply(
            db,
            user,
            {"name": "Riley", "date_of_birth": "2026-03-01", "goal_target_amount": 50_000.0},
        )

        assert len(effects) == 2
        result = await db.execute(select(Goal).where(Goal.user_id == user.id))
        assert result.scalars().all() == []

    async def test_apply_raises_422_when_date_of_birth_is_missing(
        self, db: AsyncSession, user: User
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await BirthOfChildHandler().apply(db, user, {"name": "Riley"})
        assert exc_info.value.status_code == 422


# ── Integration: the full workflow through the generic engine ──────────────


class TestBirthOfChildFullWorkflow:
    async def test_records_life_event_and_all_effects(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="birth_of_child",
            occurred_on=date(2026, 3, 1),
            inputs={
                "name": "Riley",
                "date_of_birth": "2026-03-01",
                "goal_target_amount": 80_000.0,
                "goal_target_date": (date.today() + timedelta(days=365 * 18)).isoformat(),
            },
        )

        assert life_event.event_type == "birth_of_child"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 3

    async def test_writes_both_the_family_member_added_and_life_event_recorded_audit_rows(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="birth_of_child",
            occurred_on=date.today(),
            inputs={"name": "Riley", "date_of_birth": "2026-03-01"},
        )

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id,
                AuditLog.action.in_(["family_member_added", "life_event_recorded"]),
            )
        )
        actions = {row.action for row in result.scalars().all()}
        assert actions == {"family_member_added", "life_event_recorded"}
        assert life_event.event_type == "birth_of_child"


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _BirthOfChildThenFailHandler:
    def __init__(self) -> None:
        self._real = BirthOfChildHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the member/dependent/goal writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        user_id = user.id
        await db.commit()

        life_event_service.register_handler(
            "birth_of_child_then_fail", _BirthOfChildThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="birth_of_child_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "name": "Riley",
                        "date_of_birth": "2026-03-01",
                        "goal_target_amount": 80_000.0,
                        "goal_target_date": (
                            date.today() + timedelta(days=365 * 18)
                        ).isoformat(),
                    },
                )

            await db.rollback()

            result = await db.execute(
                select(HouseholdMember).where(HouseholdMember.relationship_type == "child")
            )
            assert result.scalars().all() == []
            result = await db.execute(select(Goal).where(Goal.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("birth_of_child_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reverses_all_three_effects(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="birth_of_child",
            occurred_on=date.today(),
            inputs={
                "name": "Riley",
                "date_of_birth": "2026-03-01",
                "goal_target_amount": 80_000.0,
                "goal_target_date": (date.today() + timedelta(days=365 * 18)).isoformat(),
            },
        )
        member_id = life_event.effects[0].entity_id
        dependent_id = life_event.effects[1].entity_id
        goal_id = life_event.effects[2].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False

        member = await db.get(HouseholdMember, member_id)
        dependent = await db.get(Dependent, dependent_id)
        goal = await db.get(Goal, goal_id)
        assert member is not None and member.is_active is False
        assert dependent is not None and dependent.is_active is False
        assert goal is not None and goal.is_active is False

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="birth_of_child",
            occurred_on=date.today(),
            inputs={"name": "Riley", "date_of_birth": "2026-03-01"},
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

    async def test_cannot_undo_another_users_birth_of_child(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="birth_of_child",
            occurred_on=date.today(),
            inputs={"name": "Riley", "date_of_birth": "2026-03-01"},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Notification collision fix (shared with Marriage) ───────────────────────


class TestNotificationDoesNotDuplicate:
    async def test_exactly_one_notification_appears_for_a_birth_of_child_event(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        await life_event_service.record_life_event(
            db,
            user,
            event_type="birth_of_child",
            occurred_on=date.today(),
            inputs={"name": "Riley", "date_of_birth": "2026-03-01"},
        )
        await db.commit()

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]

        life_event_items = [i for i in items if i["source"] == "life_event"]
        family_items = [i for i in items if i["source"] == "family_member_added"]
        assert life_event_items == []
        assert len(family_items) == 1
