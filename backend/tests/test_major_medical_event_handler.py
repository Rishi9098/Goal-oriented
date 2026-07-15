"""Life Event Engine — Major Medical Event (LifeEventEngineArchitecture.md §5.13).

Covers the handler in isolation (create-expense and update-existing-
expense paths, with and without the two independent optional steps), the
full record/undo workflow through the generic engine, a rollback proof,
and verification that Dashboard/Recommendations reflect the change with
zero new calculation logic of their own.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import Asset, Expense, Liability
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import family_service, life_event_service, planning_service
from app.services.family_recommendations_service import get_family_recommendations
from app.services.life_event_service import EntityEffect
from app.services.major_medical_event_handler import MajorMedicalEventHandler


async def _make_healthcare_expense(
    db: AsyncSession, user: User, *, monthly_amount: float = 200.0
) -> Expense:
    expense = Expense(user_id=user.id, category="healthcare", monthly_amount=monthly_amount)
    db.add(expense)
    await db.flush()
    return expense


async def _make_liquid_asset(
    db: AsyncSession, user: User, *, current_value: float = 20_000.0
) -> Asset:
    asset = Asset(user_id=user.id, asset_type="savings", current_value=current_value)
    db.add(asset)
    await db.flush()
    return asset


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestMajorMedicalEventHandlerUnit:
    async def test_apply_creates_a_new_healthcare_expense_by_default(
        self, db: AsyncSession, user: User
    ):
        effects = await MajorMedicalEventHandler().apply(db, user, {"monthly_amount": 350.0})

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "expenses"
        assert effect.change_type == "create"
        assert effect.before_state is None
        assert effect.after_state["category"] == "healthcare"
        assert effect.after_state["monthly_amount"] == 350.0

        result = await db.execute(select(Expense).where(Expense.user_id == user.id))
        assert result.scalar_one().description == "Medical expense"

    async def test_apply_increases_an_existing_healthcare_expense(
        self, db: AsyncSession, user: User
    ):
        expense = await _make_healthcare_expense(db, user, monthly_amount=150.0)

        effects = await MajorMedicalEventHandler().apply(
            db, user, {"monthly_amount": 500.0, "expense_id": str(expense.id)}
        )

        assert len(effects) == 1
        effect = effects[0]
        assert effect.change_type == "update"
        assert effect.before_state["monthly_amount"] == 150.0
        assert effect.after_state["monthly_amount"] == 500.0

        await db.refresh(expense)
        assert expense.monthly_amount == 500.0

    async def test_apply_also_reduces_the_lump_sum_asset(
        self, db: AsyncSession, user: User
    ):
        funding_asset = await _make_liquid_asset(db, user, current_value=15_000.0)

        effects = await MajorMedicalEventHandler().apply(
            db,
            user,
            {
                "monthly_amount": 300.0,
                "lump_sum_asset_id": str(funding_asset.id),
                "lump_sum_amount": 5_000.0,
            },
        )

        assert len(effects) == 2
        lump_sum_effect = effects[1]
        assert lump_sum_effect.entity_table == "assets"
        assert lump_sum_effect.change_type == "update"
        assert lump_sum_effect.before_state["current_value"] == 15_000.0
        assert lump_sum_effect.after_state["current_value"] == 10_000.0

    async def test_apply_also_creates_a_financing_liability(
        self, db: AsyncSession, user: User
    ):
        effects = await MajorMedicalEventHandler().apply(
            db,
            user,
            {
                "monthly_amount": 300.0,
                "loan_balance": 8_000.0,
                "loan_monthly_payment": 250.0,
            },
        )

        assert len(effects) == 2
        liability_effect = effects[1]
        assert liability_effect.entity_table == "liabilities"
        assert liability_effect.change_type == "create"
        assert liability_effect.after_state["balance"] == 8_000.0

        result = await db.execute(select(Liability).where(Liability.user_id == user.id))
        assert result.scalar_one().liability_type == "personal_loan"

    async def test_apply_all_optional_steps_together(self, db: AsyncSession, user: User):
        funding_asset = await _make_liquid_asset(db, user, current_value=15_000.0)

        effects = await MajorMedicalEventHandler().apply(
            db,
            user,
            {
                "monthly_amount": 400.0,
                "lump_sum_asset_id": str(funding_asset.id),
                "lump_sum_amount": 5_000.0,
                "loan_balance": 10_000.0,
            },
        )

        assert len(effects) == 3
        assert [e.entity_table for e in effects] == ["expenses", "assets", "liabilities"]

    async def test_apply_raises_404_for_a_nonexistent_expense(
        self, db: AsyncSession, user: User
    ):
        from uuid import uuid4

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await MajorMedicalEventHandler().apply(
                db, user, {"monthly_amount": 300.0, "expense_id": str(uuid4())}
            )
        assert exc_info.value.status_code == 404


# ── Integration: the full workflow through the generic engine ──────────────


class TestMajorMedicalEventFullWorkflow:
    async def test_records_life_event_and_effect(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="major_medical_event",
            occurred_on=date(2026, 11, 1),
            inputs={"monthly_amount": 300.0},
        )

        assert life_event.event_type == "major_medical_event"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 1

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="major_medical_event",
            occurred_on=date.today(),
            inputs={"monthly_amount": 300.0},
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
            "event_type": "major_medical_event",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _MajorMedicalEventThenFailHandler:
    def __init__(self) -> None:
        self._real = MajorMedicalEventHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the medical event writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        funding_asset = await _make_liquid_asset(db, user, current_value=15_000.0)
        funding_asset_id = funding_asset.id
        user_id = user.id
        await db.commit()

        life_event_service.register_handler(
            "major_medical_event_then_fail", _MajorMedicalEventThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="major_medical_event_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "monthly_amount": 400.0,
                        "lump_sum_asset_id": str(funding_asset_id),
                        "lump_sum_amount": 5_000.0,
                        "loan_balance": 10_000.0,
                    },
                )

            await db.rollback()

            result = await db.execute(select(Expense).where(Expense.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(select(Liability).where(Liability.user_id == user_id))
            assert result.scalars().all() == []

            reloaded_asset = await db.get(Asset, funding_asset_id)
            assert reloaded_asset is not None
            assert reloaded_asset.current_value == 15_000.0

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("major_medical_event_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reverses_all_effects(self, db: AsyncSession, user: User):
        funding_asset = await _make_liquid_asset(db, user, current_value=15_000.0)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="major_medical_event",
            occurred_on=date.today(),
            inputs={
                "monthly_amount": 400.0,
                "lump_sum_asset_id": str(funding_asset.id),
                "lump_sum_amount": 5_000.0,
                "loan_balance": 10_000.0,
            },
        )
        expense_id = life_event.effects[0].entity_id
        liability_id = life_event.effects[2].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False

        expense = await db.get(Expense, expense_id)
        assert expense is not None and expense.is_active is False

        liability = await db.get(Liability, liability_id)
        assert liability is not None and liability.is_active is False

        await db.refresh(funding_asset)
        assert funding_asset.current_value == 15_000.0

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="major_medical_event",
            occurred_on=date.today(),
            inputs={"monthly_amount": 300.0},
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

    async def test_undo_blocked_if_the_expense_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="major_medical_event",
            occurred_on=date.today(),
            inputs={"monthly_amount": 300.0},
        )
        expense_id = life_event.effects[0].entity_id

        expense = await db.get(Expense, expense_id)
        assert expense is not None
        expense.monthly_amount = 999.0
        db.add(expense)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert any(c.entity_table == "expenses" for c in result.conflicts)

    async def test_cannot_undo_another_users_major_medical_event(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="major_medical_event",
            occurred_on=date.today(),
            inputs={"monthly_amount": 300.0},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_expenses_and_savings_rate_reflect_the_new_cost(
        self, db: AsyncSession, user: User
    ):
        from app.models.financials import IncomeSource

        db.add(IncomeSource(user_id=user.id, source_type="salary", annual_amount=60_000.0))
        await db.flush()

        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="major_medical_event",
            occurred_on=date.today(),
            inputs={"monthly_amount": 1_000.0},
        )

        after = await planning_service.get_dashboard(db, user)
        assert after.monthly_savings_rate < before.monthly_savings_rate

    async def test_low_savings_rate_recommendation_fires_after_a_large_medical_expense(
        self, db: AsyncSession, user: User
    ):
        from app.models.financials import IncomeSource

        db.add(IncomeSource(user_id=user.id, source_type="salary", annual_amount=48_000.0))
        await db.flush()
        household, _created = await family_service.get_or_create_household(db, user)

        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "low_savings_rate" for r in before_recs)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="major_medical_event",
            occurred_on=date.today(),
            inputs={"monthly_amount": 3_500.0},
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "low_savings_rate" for r in after_recs)
