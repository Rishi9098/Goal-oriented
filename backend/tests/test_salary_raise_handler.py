"""Life Event Engine — Salary Raise (LifeEventEngineArchitecture.md §5.1).

Covers the handler in isolation (income-only and income+goal-bump paths),
the full record/undo workflow through the generic engine, a rollback
proof, and verification that Dashboard and the live Recommendation Engine
reflect the change with zero new calculation logic of their own.
"""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import IncomeSource
from app.models.goal import Goal
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import family_service, life_event_service, planning_service
from app.services.family_recommendations_service import get_family_recommendations
from app.services.life_event_service import EntityEffect
from app.services.salary_raise_handler import SalaryRaiseHandler


async def _make_income(
    db: AsyncSession,
    user: User,
    *,
    annual_amount: float = 80_000.0,
    source_type: str = "salary",
) -> IncomeSource:
    income = IncomeSource(user_id=user.id, source_type=source_type, annual_amount=annual_amount)
    db.add(income)
    await db.flush()
    return income


async def _make_goal(
    db: AsyncSession,
    user: User,
    *,
    monthly_contribution: float = 200.0,
    target_amount: float = 100_000.0,
) -> Goal:
    goal = Goal(
        user_id=user.id,
        name="Test Goal",
        category="wealth",
        target_amount=target_amount,
        current_amount=1_000.0,
        target_date=date.today() + timedelta(days=365 * 10),
        monthly_contribution=monthly_contribution,
        risk_profile="balanced",
    )
    await planning_service.calculate_goal_probability(goal)
    db.add(goal)
    await db.flush()
    return goal


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestSalaryRaiseHandlerUnit:
    async def test_apply_updates_income_only_when_no_goal_is_linked(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user, annual_amount=80_000.0)

        effects = await SalaryRaiseHandler().apply(
            db,
            user,
            {"income_source_id": str(income.id), "new_annual_amount": 95_000.0},
        )

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "income_sources"
        assert effect.entity_id == income.id
        assert effect.change_type == "update"
        assert effect.before_state == {"annual_amount": 80_000.0}
        assert effect.after_state == {"annual_amount": 95_000.0}

        await db.refresh(income)
        assert income.annual_amount == 95_000.0

    async def test_apply_also_updates_a_linked_goals_monthly_contribution(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user, annual_amount=80_000.0)
        goal = await _make_goal(db, user, monthly_contribution=200.0)

        effects = await SalaryRaiseHandler().apply(
            db,
            user,
            {
                "income_source_id": str(income.id),
                "new_annual_amount": 95_000.0,
                "goal_id": str(goal.id),
                "new_monthly_contribution": 350.0,
            },
        )

        assert len(effects) == 2
        income_effect, goal_effect = effects
        assert income_effect.entity_table == "income_sources"
        assert goal_effect.entity_table == "goals"
        assert goal_effect.entity_id == goal.id
        assert goal_effect.change_type == "update"
        assert goal_effect.before_state["monthly_contribution"] == 200.0
        assert goal_effect.after_state["monthly_contribution"] == 350.0
        # ADR-001: monthly_contribution is a Calculation Context field, so
        # probability/on_track must have been recalculated and captured too
        # — not a second copy of that rule, just proof this handler routed
        # through planning_service.update_goal_fields rather than a bespoke
        # setattr.
        assert "probability" in goal_effect.after_state
        assert "on_track" in goal_effect.after_state

        await db.refresh(goal)
        assert goal.monthly_contribution == 350.0

    async def test_apply_ignores_goal_id_when_new_monthly_contribution_is_absent(
        self, db: AsyncSession, user: User
    ):
        """Explicit opt-in required for the linked-goal step — a goal_id
        with no accompanying new_monthly_contribution must not trigger a
        goal write at all."""
        income = await _make_income(db, user)
        goal = await _make_goal(db, user, monthly_contribution=200.0)

        effects = await SalaryRaiseHandler().apply(
            db,
            user,
            {
                "income_source_id": str(income.id),
                "new_annual_amount": 90_000.0,
                "goal_id": str(goal.id),
            },
        )

        assert len(effects) == 1
        await db.refresh(goal)
        assert goal.monthly_contribution == 200.0

    async def test_apply_raises_for_a_nonexistent_income_source(
        self, db: AsyncSession, user: User
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await SalaryRaiseHandler().apply(
                db, user, {"income_source_id": str(uuid.uuid4()), "new_annual_amount": 100_000.0}
            )
        assert exc_info.value.status_code == 404

    async def test_apply_raises_for_another_users_income_source(
        self, db: AsyncSession, user: User, other_user: User
    ):
        from fastapi import HTTPException

        someone_elses_income = await _make_income(db, other_user, annual_amount=60_000.0)

        with pytest.raises(HTTPException) as exc_info:
            await SalaryRaiseHandler().apply(
                db,
                user,
                {
                    "income_source_id": str(someone_elses_income.id),
                    "new_annual_amount": 999_000.0,
                },
            )
        assert exc_info.value.status_code == 404

        await db.refresh(someone_elses_income)
        assert someone_elses_income.annual_amount == 60_000.0

    async def test_apply_raises_for_another_users_linked_goal(
        self, db: AsyncSession, user: User, other_user: User
    ):
        from fastapi import HTTPException

        income = await _make_income(db, user)
        someone_elses_goal = await _make_goal(db, other_user)

        with pytest.raises(HTTPException) as exc_info:
            await SalaryRaiseHandler().apply(
                db,
                user,
                {
                    "income_source_id": str(income.id),
                    "new_annual_amount": 90_000.0,
                    "goal_id": str(someone_elses_goal.id),
                    "new_monthly_contribution": 500.0,
                },
            )
        assert exc_info.value.status_code == 404

        # The income write (first, before the goal lookup fails) is still
        # visible on this session — proving the *ordering* is as expected,
        # not that it is durable: record_life_event's rollback discipline
        # is what makes the whole thing atomic (see TestRollback below).
        await db.refresh(income)
        assert income.annual_amount == 90_000.0


# ── Integration: the full workflow through the generic engine ──────────────


class TestSalaryRaiseFullWorkflow:
    async def test_records_life_event_and_effect_and_updates_income(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user, annual_amount=70_000.0)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date(2026, 4, 1),
            inputs={"income_source_id": str(income.id), "new_annual_amount": 82_000.0},
        )

        assert life_event.event_type == "salary_raise"
        assert life_event.status == "applied"
        assert life_event.occurred_on == date(2026, 4, 1)
        assert len(life_event.effects) == 1
        assert life_event.effects[0].entity_table == "income_sources"
        assert life_event.effects[0].entity_id == income.id

        await db.refresh(income)
        assert income.annual_amount == 82_000.0

    async def test_records_both_effects_when_a_goal_is_linked(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user, annual_amount=70_000.0)
        goal = await _make_goal(db, user, monthly_contribution=100.0)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={
                "income_source_id": str(income.id),
                "new_annual_amount": 82_000.0,
                "goal_id": str(goal.id),
                "new_monthly_contribution": 400.0,
            },
        )

        assert len(life_event.effects) == 2
        tables = {effect.entity_table for effect in life_event.effects}
        assert tables == {"income_sources", "goals"}

        await db.refresh(goal)
        assert goal.monthly_contribution == 400.0

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        income = await _make_income(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={"income_source_id": str(income.id), "new_annual_amount": 100_000.0},
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
            "event_type": "salary_raise",
        }


# ── Rollback: a failure after the write must leave nothing durable ─────────


class _SalaryRaiseThenFailHandler:
    """Wraps the real handler so both real writes actually happen (and get
    flushed), then fails — proving record_life_event's "never commit"
    discipline means a caller's rollback discards both already-flushed
    changes, not just the LifeEvent/LifeEventEffect rows."""

    def __init__(self) -> None:
        self._real = SalaryRaiseHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the income/goal writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user, annual_amount=60_000.0)
        goal = await _make_goal(db, user, monthly_contribution=150.0)
        income_id = income.id
        goal_id = goal.id
        user_id = user.id
        # Commits the income/goal *creation* as an established checkpoint —
        # exactly as it would already be durable from an earlier, separate
        # request in real use. Only the salary-raise attempt below (a
        # second, failing "request") is what this test proves rolls back
        # cleanly.
        await db.commit()
        life_event_service.register_handler(
            "salary_raise_then_fail", _SalaryRaiseThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="salary_raise_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "income_source_id": str(income_id),
                        "new_annual_amount": 120_000.0,
                        "goal_id": str(goal_id),
                        "new_monthly_contribution": 900.0,
                    },
                )

            await db.rollback()
            # session.rollback() expires every already-loaded object's
            # attributes — income_id/goal_id/user_id were captured as plain
            # UUIDs above specifically so nothing below touches an expired
            # ORM attribute outside an awaited context.

            reloaded_income = await db.get(IncomeSource, income_id)
            assert reloaded_income is not None
            assert reloaded_income.annual_amount == 60_000.0

            reloaded_goal = await db.get(Goal, goal_id)
            assert reloaded_goal is not None
            assert reloaded_goal.monthly_contribution == 150.0

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(
                select(AuditLog).where(
                    AuditLog.user_id == user_id, AuditLog.action == "life_event_recorded"
                )
            )
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("salary_raise_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reverts_income_only_when_no_goal_was_linked(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user, annual_amount=75_000.0)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={"income_source_id": str(income.id), "new_annual_amount": 88_000.0},
        )

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        assert result.conflicts == []

        await db.refresh(income)
        assert income.annual_amount == 75_000.0

        await db.refresh(life_event)
        assert life_event.status == "undone"
        assert life_event.undone_at is not None

    async def test_undo_reverts_both_income_and_goal_when_linked(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user, annual_amount=75_000.0)
        goal = await _make_goal(db, user, monthly_contribution=250.0)
        original_probability = goal.probability

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={
                "income_source_id": str(income.id),
                "new_annual_amount": 88_000.0,
                "goal_id": str(goal.id),
                "new_monthly_contribution": 500.0,
            },
        )

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        await db.refresh(income)
        assert income.annual_amount == 75_000.0

        await db.refresh(goal)
        assert goal.monthly_contribution == 250.0
        assert goal.probability == original_probability

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={"income_source_id": str(income.id), "new_annual_amount": 100_000.0},
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

    async def test_undo_blocked_if_the_income_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        income = await _make_income(db, user, annual_amount=75_000.0)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={"income_source_id": str(income.id), "new_annual_amount": 88_000.0},
        )

        # Simulate something independently touching the income after the
        # raise was recorded.
        income.annual_amount = 999_000.0
        db.add(income)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert len(result.conflicts) == 1
        assert result.conflicts[0].entity_table == "income_sources"

        unchanged = await db.get(IncomeSource, income.id)
        assert unchanged is not None
        assert unchanged.annual_amount == 999_000.0

    async def test_cannot_undo_another_users_salary_raise(
        self, db: AsyncSession, user: User, other_user: User
    ):
        income = await _make_income(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={"income_source_id": str(income.id), "new_annual_amount": 100_000.0},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_income_and_savings_rate_rise_after_raise(
        self, db: AsyncSession, user: User
    ):
        from app.models.financials import Expense

        income = await _make_income(db, user, annual_amount=60_000.0)
        db.add(Expense(user_id=user.id, category="housing", monthly_amount=4_000.0))
        await db.flush()

        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={"income_source_id": str(income.id), "new_annual_amount": 120_000.0},
        )

        after = await planning_service.get_dashboard(db, user)
        assert after.monthly_savings_rate > before.monthly_savings_rate

    async def test_low_savings_rate_recommendation_stops_firing_after_raise(
        self, db: AsyncSession, user: User
    ):
        from app.models.financials import Expense

        # A low salary against high expenses puts savings_rate below
        # family_recommendations_service's own LOW_SAVINGS_RATE_THRESHOLD —
        # reused, not restated, by this test.
        income = await _make_income(db, user, annual_amount=30_000.0)
        db.add(Expense(user_id=user.id, category="housing", monthly_amount=2_300.0))
        await db.flush()
        household, _created = await family_service.get_or_create_household(db, user)

        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "low_savings_rate" for r in before_recs)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="salary_raise",
            occurred_on=date.today(),
            inputs={"income_source_id": str(income.id), "new_annual_amount": 150_000.0},
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "low_savings_rate" for r in after_recs)
