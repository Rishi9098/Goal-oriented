"""Life Event Engine — Business Start (LifeEventEngineArchitecture.md §5.14).

Covers the handler in isolation (no-optional-steps and all-optional-steps
paths), the full record/undo workflow through the generic engine, a
rollback proof, and confirms no income_sources row is ever created (the
architecture's own explicit design constraint for this event).
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.life_event import LifeEvent
from app.models.profile import UserProfile
from app.models.user import User
from app.services import life_event_service
from app.services.business_start_handler import BusinessStartHandler
from app.services.life_event_service import EntityEffect


async def _make_liquid_asset(
    db: AsyncSession, user: User, *, current_value: float = 30_000.0
) -> Asset:
    asset = Asset(user_id=user.id, asset_type="savings", current_value=current_value)
    db.add(asset)
    await db.flush()
    return asset


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestBusinessStartHandlerUnit:
    async def test_apply_sets_employment_status_with_no_optional_steps(
        self, db: AsyncSession, user: User
    ):
        effects = await BusinessStartHandler().apply(db, user, {})

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "user_profiles"
        assert effect.after_state["employment_status"] == "self_employed"

        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        assert result.scalar_one().employment_status == "self_employed"

    async def test_apply_never_creates_an_income_source(
        self, db: AsyncSession, user: User
    ):
        await BusinessStartHandler().apply(
            db,
            user,
            {
                "ongoing_expense_amount": 500.0,
                "loan_balance": 20_000.0,
            },
        )

        result = await db.execute(select(IncomeSource).where(IncomeSource.user_id == user.id))
        assert result.scalars().all() == []

    async def test_apply_reduces_the_funding_asset(self, db: AsyncSession, user: User):
        funding_asset = await _make_liquid_asset(db, user, current_value=30_000.0)

        effects = await BusinessStartHandler().apply(
            db,
            user,
            {"funding_asset_id": str(funding_asset.id), "funding_amount": 10_000.0},
        )

        assert len(effects) == 2
        asset_effect = effects[1]
        assert asset_effect.entity_table == "assets"
        assert asset_effect.change_type == "update"
        assert asset_effect.before_state["current_value"] == 30_000.0
        assert asset_effect.after_state["current_value"] == 20_000.0

    async def test_apply_creates_an_ongoing_business_expense(
        self, db: AsyncSession, user: User
    ):
        effects = await BusinessStartHandler().apply(
            db, user, {"ongoing_expense_amount": 800.0}
        )

        assert len(effects) == 2
        expense_effect = effects[1]
        assert expense_effect.entity_table == "expenses"
        assert expense_effect.change_type == "create"
        assert expense_effect.after_state["category"] == "business"
        assert expense_effect.after_state["monthly_amount"] == 800.0

    async def test_apply_creates_a_business_loan_as_other_liability_type(
        self, db: AsyncSession, user: User
    ):
        effects = await BusinessStartHandler().apply(
            db,
            user,
            {"loan_balance": 25_000.0, "loan_description": "SBA startup loan"},
        )

        assert len(effects) == 2
        liability_effect = effects[1]
        assert liability_effect.entity_table == "liabilities"
        assert liability_effect.after_state["balance"] == 25_000.0

        result = await db.execute(select(Liability).where(Liability.user_id == user.id))
        liability = result.scalar_one()
        # Honest schema gap: no dedicated business_loan enum value yet.
        assert liability.liability_type == "other"
        assert liability.description == "SBA startup loan"

    async def test_apply_all_optional_steps_together(self, db: AsyncSession, user: User):
        funding_asset = await _make_liquid_asset(db, user, current_value=30_000.0)

        effects = await BusinessStartHandler().apply(
            db,
            user,
            {
                "funding_asset_id": str(funding_asset.id),
                "funding_amount": 10_000.0,
                "ongoing_expense_amount": 800.0,
                "loan_balance": 25_000.0,
            },
        )

        assert len(effects) == 4
        assert [e.entity_table for e in effects] == [
            "user_profiles",
            "assets",
            "expenses",
            "liabilities",
        ]


# ── Integration: the full workflow through the generic engine ──────────────


class TestBusinessStartFullWorkflow:
    async def test_records_life_event_and_effect(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="business_start",
            occurred_on=date(2026, 12, 1),
            inputs={},
        )

        assert life_event.event_type == "business_start"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 1

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="business_start", occurred_on=date.today(), inputs={}
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
            "event_type": "business_start",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _BusinessStartThenFailHandler:
    def __init__(self) -> None:
        self._real = BusinessStartHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the business start writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        funding_asset = await _make_liquid_asset(db, user, current_value=30_000.0)
        funding_asset_id = funding_asset.id
        user_id = user.id
        await db.commit()

        life_event_service.register_handler(
            "business_start_then_fail", _BusinessStartThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="business_start_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "funding_asset_id": str(funding_asset_id),
                        "funding_amount": 10_000.0,
                        "ongoing_expense_amount": 800.0,
                        "loan_balance": 25_000.0,
                    },
                )

            await db.rollback()

            reloaded_asset = await db.get(Asset, funding_asset_id)
            assert reloaded_asset is not None
            assert reloaded_asset.current_value == 30_000.0

            result = await db.execute(select(Expense).where(Expense.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(select(Liability).where(Liability.user_id == user_id))
            assert result.scalars().all() == []

            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            assert profile is None or profile.employment_status != "self_employed"

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("business_start_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reverses_all_effects_when_profile_pre_exists(
        self, db: AsyncSession, user: User
    ):
        # Pre-existing profile makes the profile effect an "update", not
        # a "create" — see Retirement's own report for why a fresh
        # profile create cannot be reversed by the generic engine
        # (UserProfile has no is_active column). This is the same,
        # already-documented limitation, not re-derived here.
        db.add(UserProfile(user_id=user.id, employment_status="employed"))
        await db.flush()
        funding_asset = await _make_liquid_asset(db, user, current_value=30_000.0)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="business_start",
            occurred_on=date.today(),
            inputs={
                "funding_asset_id": str(funding_asset.id),
                "funding_amount": 10_000.0,
                "ongoing_expense_amount": 800.0,
                "loan_balance": 25_000.0,
            },
        )
        expense_id = life_event.effects[2].entity_id
        liability_id = life_event.effects[3].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False

        result_profile = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        assert result_profile.scalar_one().employment_status == "employed"

        await db.refresh(funding_asset)
        assert funding_asset.current_value == 30_000.0

        expense = await db.get(Expense, expense_id)
        liability = await db.get(Liability, liability_id)
        assert expense is not None and expense.is_active is False
        assert liability is not None and liability.is_active is False

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="business_start", occurred_on=date.today(), inputs={}
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

    async def test_cannot_undo_another_users_business_start(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="business_start", occurred_on=date.today(), inputs={}
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)
