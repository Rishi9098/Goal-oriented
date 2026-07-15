"""Life Event Engine — Education Planning.

Not one of the architecture's original 15 catalogued events — a pure
goal-creation event (see this event's own module docstring). Covers the
handler in isolation, the full record/undo workflow through the generic
engine, a rollback proof, and verification that Dashboard reflects the
new goal with zero new calculation logic of its own.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.goal import Goal
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import life_event_service, planning_service
from app.services.education_planning_handler import EducationPlanningHandler
from app.services.life_event_service import EntityEffect


def _target_date() -> str:
    return (date.today() + timedelta(days=365 * 12)).isoformat()


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestEducationPlanningHandlerUnit:
    async def test_apply_creates_an_education_goal_with_defaults(
        self, db: AsyncSession, user: User
    ):
        effects = await EducationPlanningHandler().apply(
            db,
            user,
            {
                "name": "Kid's College Fund",
                "target_amount": 75_000.0,
                "target_date": _target_date(),
            },
        )

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "goals"
        assert effect.change_type == "create"
        assert effect.before_state is None
        assert effect.after_state["category"] == "education"
        assert effect.after_state["target_amount"] == 75_000.0
        assert effect.after_state["current_amount"] == 0.0
        assert effect.after_state["monthly_contribution"] == 0.0
        assert "probability" in effect.after_state

        result = await db.execute(select(Goal).where(Goal.id == effect.entity_id))
        goal = result.scalar_one()
        assert goal.name == "Kid's College Fund"
        assert goal.risk_profile == "balanced"
        assert goal.is_active is True

    async def test_apply_honors_explicit_optional_fields(
        self, db: AsyncSession, user: User
    ):
        effects = await EducationPlanningHandler().apply(
            db,
            user,
            {
                "name": "Grad School Fund",
                "target_amount": 50_000.0,
                "target_date": _target_date(),
                "current_amount": 5_000.0,
                "monthly_contribution": 300.0,
                "risk_profile": "aggressive",
            },
        )

        after = effects[0].after_state
        assert after["current_amount"] == 5_000.0
        assert after["monthly_contribution"] == 300.0
        assert after["risk_profile"] == "aggressive"


# ── Integration: the full workflow through the generic engine ──────────────


class TestEducationPlanningFullWorkflow:
    async def test_records_life_event_and_effect_and_creates_the_goal(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="education_planning",
            occurred_on=date(2026, 8, 1),
            inputs={
                "name": "College Fund",
                "target_amount": 80_000.0,
                "target_date": _target_date(),
            },
        )

        assert life_event.event_type == "education_planning"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 1

        result = await db.execute(select(Goal).where(Goal.user_id == user.id))
        assert result.scalar_one().category == "education"

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="education_planning",
            occurred_on=date.today(),
            inputs={
                "name": "College Fund",
                "target_amount": 60_000.0,
                "target_date": _target_date(),
            },
        )

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id, AuditLog.action == "life_event_recorded"
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].after_state == {
            "life_event_id": str(life_event.id),
            "event_type": "education_planning",
        }


# ── Rollback: a failure after the write must leave nothing durable ─────────


class _EducationPlanningThenFailHandler:
    def __init__(self) -> None:
        self._real = EducationPlanningHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the goal was created")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        user_id = user.id
        await db.commit()
        life_event_service.register_handler(
            "education_planning_then_fail", _EducationPlanningThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="education_planning_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "name": "College Fund",
                        "target_amount": 90_000.0,
                        "target_date": _target_date(),
                    },
                )

            await db.rollback()

            result = await db.execute(select(Goal).where(Goal.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("education_planning_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_soft_deletes_the_created_goal(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="education_planning",
            occurred_on=date.today(),
            inputs={
                "name": "College Fund",
                "target_amount": 70_000.0,
                "target_date": _target_date(),
            },
        )
        goal_id = life_event.effects[0].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        goal = await db.get(Goal, goal_id)
        assert goal is not None
        assert goal.is_active is False

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="education_planning",
            occurred_on=date.today(),
            inputs={
                "name": "College Fund",
                "target_amount": 40_000.0,
                "target_date": _target_date(),
            },
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

    async def test_undo_blocked_if_the_goal_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="education_planning",
            occurred_on=date.today(),
            inputs={
                "name": "College Fund",
                "target_amount": 40_000.0,
                "target_date": _target_date(),
            },
        )
        goal_id = life_event.effects[0].entity_id

        goal = await db.get(Goal, goal_id)
        assert goal is not None
        goal.current_amount = 999_999.0
        db.add(goal)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert any(c.entity_table == "goals" for c in result.conflicts)

    async def test_cannot_undo_another_users_education_planning(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="education_planning",
            occurred_on=date.today(),
            inputs={
                "name": "College Fund",
                "target_amount": 40_000.0,
                "target_date": _target_date(),
            },
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard verification ───────────────────────────────────────────────────


class TestDashboardIntegration:
    async def test_dashboard_reflects_the_new_education_goal(
        self, db: AsyncSession, user: User
    ):
        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="education_planning",
            occurred_on=date.today(),
            inputs={
                "name": "College Fund",
                "target_amount": 60_000.0,
                "target_date": _target_date(),
            },
        )

        after = await planning_service.get_dashboard(db, user)
        assert after.goal_count == before.goal_count + 1
