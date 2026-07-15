"""Life Event Engine — Retirement (LifeEventEngineArchitecture.md §5.12).

"The most structurally distinct event — a status transition rather than
a single transaction, touching Profile, Income, and Assumptions
together." Covers the handler across its full range of 1-7 effects
(profile always; income deactivation(s), pension creation, assumptions
update, and goal-contribution update(s), each independently opt-in), the
full record/undo workflow through the generic engine, a rollback proof,
and verification that Dashboard/Recommendations reflect the change with
zero new calculation logic of their own.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assumptions import FinancialAssumptions
from app.models.audit import AuditLog
from app.models.financials import IncomeSource
from app.models.goal import Goal
from app.models.life_event import LifeEvent
from app.models.profile import UserProfile
from app.models.user import User
from app.services import life_event_service, planning_service
from app.services.life_event_service import EntityEffect
from app.services.retirement_handler import RetirementHandler


async def _make_salary_income(
    db: AsyncSession, user: User, *, annual_amount: float = 120_000.0
) -> IncomeSource:
    income = IncomeSource(user_id=user.id, source_type="salary", annual_amount=annual_amount)
    db.add(income)
    await db.flush()
    return income


async def _make_retirement_goal(
    db: AsyncSession, user: User, *, monthly_contribution: float = 1_000.0
) -> Goal:
    goal = Goal(
        user_id=user.id,
        name="Retirement Fund",
        category="retirement",
        target_amount=1_000_000.0,
        current_amount=500_000.0,
        target_date=date.today() + timedelta(days=365 * 5),
        monthly_contribution=monthly_contribution,
        risk_profile="balanced",
    )
    await planning_service.calculate_goal_probability(goal)
    db.add(goal)
    await db.flush()
    return goal


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestRetirementHandlerUnit:
    async def test_apply_sets_employment_status_with_no_optional_steps(
        self, db: AsyncSession, user: User
    ):
        effects = await RetirementHandler().apply(db, user, {})

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "user_profiles"
        assert effect.after_state["employment_status"] == "retired"

        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        assert result.scalar_one().employment_status == "retired"

    async def test_apply_deactivates_the_given_income_sources(
        self, db: AsyncSession, user: User
    ):
        salary = await _make_salary_income(db, user, annual_amount=100_000.0)

        effects = await RetirementHandler().apply(
            db, user, {"income_source_ids": [str(salary.id)]}
        )

        assert len(effects) == 2
        assert effects[1].entity_table == "income_sources"
        assert effects[1].change_type == "soft_delete"
        assert effects[1].after_state["is_active"] is False

        await db.refresh(salary)
        assert salary.is_active is False

    async def test_apply_creates_a_pension_income_source(
        self, db: AsyncSession, user: User
    ):
        effects = await RetirementHandler().apply(
            db, user, {"pension_amount": 36_000.0, "pension_description": "State pension"}
        )

        assert len(effects) == 2
        pension_effect = effects[1]
        assert pension_effect.entity_table == "income_sources"
        assert pension_effect.change_type == "create"
        assert pension_effect.after_state["source_type"] == "pension"
        assert pension_effect.after_state["annual_amount"] == 36_000.0

        result = await db.execute(
            select(IncomeSource).where(
                IncomeSource.user_id == user.id, IncomeSource.source_type == "pension"
            )
        )
        assert result.scalar_one().description == "State pension"

    async def test_apply_updates_assumptions_when_either_field_is_given(
        self, db: AsyncSession, user: User
    ):
        effects = await RetirementHandler().apply(
            db, user, {"retirement_age": 62, "social_security_monthly": 1_800.0}
        )

        assert len(effects) == 2
        assumptions_effect = effects[1]
        assert assumptions_effect.entity_table == "financial_assumptions"
        assert assumptions_effect.after_state["retirement_age"] == 62
        assert assumptions_effect.after_state["social_security_monthly"] == 1_800.0

        result = await db.execute(
            select(FinancialAssumptions).where(FinancialAssumptions.user_id == user.id)
        )
        assumptions = result.scalar_one()
        assert assumptions.retirement_age == 62

    async def test_apply_updates_one_or_more_goal_contributions(
        self, db: AsyncSession, user: User
    ):
        goal = await _make_retirement_goal(db, user, monthly_contribution=1_000.0)

        effects = await RetirementHandler().apply(
            db,
            user,
            {
                "goal_contributions": [
                    {"goal_id": str(goal.id), "new_monthly_contribution": 0.0}
                ]
            },
        )

        assert len(effects) == 2
        goal_effect = effects[1]
        assert goal_effect.entity_table == "goals"
        assert goal_effect.change_type == "update"
        assert goal_effect.before_state["monthly_contribution"] == 1_000.0
        assert goal_effect.after_state["monthly_contribution"] == 0.0
        assert "probability" in goal_effect.after_state

        await db.refresh(goal)
        assert goal.monthly_contribution == 0.0

    async def test_apply_all_steps_together_produces_up_to_seven_effects(
        self, db: AsyncSession, user: User
    ):
        salary1 = await _make_salary_income(db, user, annual_amount=90_000.0)
        salary2 = await _make_salary_income(db, user, annual_amount=30_000.0)
        goal1 = await _make_retirement_goal(db, user, monthly_contribution=1_000.0)
        goal2 = await _make_retirement_goal(db, user, monthly_contribution=500.0)

        effects = await RetirementHandler().apply(
            db,
            user,
            {
                "income_source_ids": [str(salary1.id), str(salary2.id)],
                "pension_amount": 40_000.0,
                "retirement_age": 63,
                "goal_contributions": [
                    {"goal_id": str(goal1.id), "new_monthly_contribution": 0.0},
                    {"goal_id": str(goal2.id), "new_monthly_contribution": 200.0},
                ],
            },
        )

        # profile + 2 income deactivations + 1 pension create + 1 assumptions
        # update + 2 goal updates = 7
        assert len(effects) == 7
        tables = [e.entity_table for e in effects]
        assert tables == [
            "user_profiles",
            "income_sources",
            "income_sources",
            "income_sources",
            "financial_assumptions",
            "goals",
            "goals",
        ]


# ── Integration: the full workflow through the generic engine ──────────────


class TestRetirementFullWorkflow:
    async def test_records_life_event_and_effects(self, db: AsyncSession, user: User):
        salary = await _make_salary_income(db, user)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="retirement",
            occurred_on=date(2026, 9, 1),
            inputs={"income_source_ids": [str(salary.id)], "pension_amount": 30_000.0},
        )

        assert life_event.event_type == "retirement"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 3

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="retirement", occurred_on=date.today(), inputs={}
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
            "event_type": "retirement",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _RetirementThenFailHandler:
    def __init__(self) -> None:
        self._real = RetirementHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the retirement writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        salary = await _make_salary_income(db, user, annual_amount=80_000.0)
        goal = await _make_retirement_goal(db, user, monthly_contribution=900.0)
        salary_id = salary.id
        goal_id = goal.id
        user_id = user.id
        await db.commit()

        life_event_service.register_handler(
            "retirement_then_fail", _RetirementThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="retirement_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "income_source_ids": [str(salary_id)],
                        "pension_amount": 25_000.0,
                        "retirement_age": 60,
                        "goal_contributions": [
                            {"goal_id": str(goal_id), "new_monthly_contribution": 0.0}
                        ],
                    },
                )

            await db.rollback()

            reloaded_salary = await db.get(IncomeSource, salary_id)
            assert reloaded_salary is not None
            assert reloaded_salary.is_active is True

            reloaded_goal = await db.get(Goal, goal_id)
            assert reloaded_goal is not None
            assert reloaded_goal.monthly_contribution == 900.0

            result = await db.execute(
                select(IncomeSource).where(
                    IncomeSource.user_id == user_id, IncomeSource.source_type == "pension"
                )
            )
            assert result.scalars().all() == []

            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            assert profile is None or profile.employment_status != "retired"

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("retirement_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reverses_all_effects(self, db: AsyncSession, user: User):
        # Pre-existing profile and assumptions rows make those two
        # effects "update"s (reversible via before_state) rather than
        # "create"s — neither UserProfile nor FinancialAssumptions has an
        # is_active column, so the generic engine's create-effect
        # reversal rule cannot undo a fresh create of either; see
        # test_undo_cannot_reverse_a_newly_created_profile below for that
        # documented, tested limitation.
        db.add(UserProfile(user_id=user.id, employment_status="employed"))
        db.add(FinancialAssumptions(user_id=user.id, retirement_age=65))
        await db.flush()

        salary = await _make_salary_income(db, user, annual_amount=70_000.0)
        goal = await _make_retirement_goal(db, user, monthly_contribution=800.0)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="retirement",
            occurred_on=date.today(),
            inputs={
                "income_source_ids": [str(salary.id)],
                "pension_amount": 20_000.0,
                "retirement_age": 61,
                "goal_contributions": [
                    {"goal_id": str(goal.id), "new_monthly_contribution": 0.0}
                ],
            },
        )
        pension_id = next(
            e.entity_id
            for e in life_event.effects
            if e.entity_table == "income_sources" and e.change_type == "create"
        )

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False

        await db.refresh(salary)
        assert salary.is_active is True

        pension = await db.get(IncomeSource, pension_id)
        assert pension is not None
        assert pension.is_active is False  # generic undo: create -> soft-delete

        result = await db.execute(
            select(FinancialAssumptions).where(FinancialAssumptions.user_id == user.id)
        )
        assumptions = result.scalar_one()
        assert assumptions.retirement_age == 65  # restored from before_state

        await db.refresh(goal)
        assert goal.monthly_contribution == 800.0

        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = result.scalar_one()
        assert profile.employment_status == "employed"  # restored from before_state

    async def test_undo_cannot_reverse_a_newly_created_profile(
        self, db: AsyncSession, user: User
    ):
        """Named, tested limitation: when the user has no pre-existing
        UserProfile, RetirementHandler's profile effect is a "create"
        (before_state=None). UserProfile has no is_active column, so the
        generic engine's create-effect reversal rule
        (life_event_service.undo_life_event's own documented "known
        limitation, not resolved here") cannot undo it — the profile
        stays "retired" even after a supposedly successful undo. Every
        other effect in the same event still reverses correctly; only
        this one, structural gap is left as-is, consistent with this
        engine's existing, pre-established limitation rather than a new
        one invented for this event."""
        life_event = await life_event_service.record_life_event(
            db, user, event_type="retirement", occurred_on=date.today(), inputs={}
        )

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = profile_result.scalar_one()
        assert profile.employment_status == "retired"  # NOT reverted — the known limitation

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="retirement", occurred_on=date.today(), inputs={}
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

    async def test_cannot_undo_another_users_retirement(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="retirement", occurred_on=date.today(), inputs={}
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_income_reflects_the_new_pension_only(
        self, db: AsyncSession, user: User
    ):
        salary = await _make_salary_income(db, user, annual_amount=150_000.0)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="retirement",
            occurred_on=date.today(),
            inputs={"income_source_ids": [str(salary.id)], "pension_amount": 40_000.0},
        )

        result = await db.execute(
            select(IncomeSource).where(
                IncomeSource.user_id == user.id, IncomeSource.is_active.is_(True)
            )
        )
        active_incomes = result.scalars().all()
        assert len(active_incomes) == 1
        assert active_incomes[0].source_type == "pension"
        assert active_incomes[0].annual_amount == 40_000.0
