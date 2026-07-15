"""Life Event Engine — Business Sale (LifeEventEngineArchitecture.md §5.15).

The final event in this run's 17-event sequence. Covers the handler
across its full range of 1-4 effects (proceeds always; business-liability
payoff, income-payout creation, and employment-status revert, each
independently opt-in), the full record/undo workflow through the generic
engine, a rollback proof, and verification that Dashboard/Recommendations
reflect the change with zero new calculation logic of their own.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import Asset, IncomeSource, Liability
from app.models.life_event import LifeEvent
from app.models.profile import UserProfile
from app.models.user import User
from app.services import family_service, life_event_service, planning_service
from app.services.business_sale_handler import BusinessSaleHandler
from app.services.family_recommendations_service import get_family_recommendations
from app.services.life_event_service import EntityEffect


async def _make_liquid_asset(
    db: AsyncSession, user: User, *, current_value: float = 10_000.0
) -> Asset:
    asset = Asset(user_id=user.id, asset_type="savings", current_value=current_value)
    db.add(asset)
    await db.flush()
    return asset


async def _make_business_liability(
    db: AsyncSession, user: User, *, balance: float = 30_000.0
) -> Liability:
    liability = Liability(
        user_id=user.id,
        liability_type="other",
        description="Business loan",
        balance=balance,
        interest_rate=0.08,
        monthly_payment=800.0,
    )
    db.add(liability)
    await db.flush()
    return liability


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestBusinessSaleHandlerUnit:
    async def test_apply_creates_a_new_proceeds_asset_by_default(
        self, db: AsyncSession, user: User
    ):
        effects = await BusinessSaleHandler().apply(db, user, {"net_proceeds": 200_000.0})

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "assets"
        assert effect.change_type == "create"
        assert effect.after_state["current_value"] == 200_000.0
        assert effect.after_state["asset_type"] == "savings"

    async def test_apply_adds_proceeds_to_an_existing_asset(
        self, db: AsyncSession, user: User
    ):
        savings = await _make_liquid_asset(db, user, current_value=15_000.0)

        effects = await BusinessSaleHandler().apply(
            db, user, {"net_proceeds": 100_000.0, "proceeds_asset_id": str(savings.id)}
        )

        assert len(effects) == 1
        effect = effects[0]
        assert effect.change_type == "update"
        assert effect.before_state["current_value"] == 15_000.0
        assert effect.after_state["current_value"] == 115_000.0

        await db.refresh(savings)
        assert savings.current_value == 115_000.0

    async def test_apply_also_pays_off_a_business_liability(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_business_liability(db, user, balance=25_000.0)

        effects = await BusinessSaleHandler().apply(
            db,
            user,
            {"net_proceeds": 150_000.0, "business_liability_id": str(liability.id)},
        )

        assert len(effects) == 2
        liability_effect = effects[1]
        assert liability_effect.entity_table == "liabilities"
        assert liability_effect.change_type == "soft_delete"
        assert liability_effect.after_state["is_active"] is False

        await db.refresh(liability)
        assert liability.is_active is False

    async def test_apply_also_creates_an_income_payout(self, db: AsyncSession, user: User):
        effects = await BusinessSaleHandler().apply(
            db, user, {"net_proceeds": 50_000.0, "income_amount": 12_000.0}
        )

        assert len(effects) == 2
        income_effect = effects[1]
        assert income_effect.entity_table == "income_sources"
        assert income_effect.change_type == "create"
        assert income_effect.after_state["source_type"] == "other"
        assert income_effect.after_state["annual_amount"] == 12_000.0

    async def test_apply_also_reverts_employment_status(self, db: AsyncSession, user: User):
        db.add(UserProfile(user_id=user.id, employment_status="self_employed"))
        await db.flush()

        effects = await BusinessSaleHandler().apply(
            db,
            user,
            {"net_proceeds": 50_000.0, "new_employment_status": "employed"},
        )

        assert len(effects) == 2
        profile_effect = effects[1]
        assert profile_effect.entity_table == "user_profiles"
        assert profile_effect.change_type == "update"
        assert profile_effect.before_state["employment_status"] == "self_employed"
        assert profile_effect.after_state["employment_status"] == "employed"

    async def test_apply_all_optional_steps_together(self, db: AsyncSession, user: User):
        savings = await _make_liquid_asset(db, user, current_value=15_000.0)
        liability = await _make_business_liability(db, user, balance=25_000.0)
        db.add(UserProfile(user_id=user.id, employment_status="self_employed"))
        await db.flush()

        effects = await BusinessSaleHandler().apply(
            db,
            user,
            {
                "net_proceeds": 150_000.0,
                "proceeds_asset_id": str(savings.id),
                "business_liability_id": str(liability.id),
                "income_amount": 12_000.0,
                "new_employment_status": "employed",
            },
        )

        assert len(effects) == 4
        assert [e.entity_table for e in effects] == [
            "assets",
            "liabilities",
            "income_sources",
            "user_profiles",
        ]


# ── Integration: the full workflow through the generic engine ──────────────


class TestBusinessSaleFullWorkflow:
    async def test_records_life_event_and_effect(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="business_sale",
            occurred_on=date(2027, 1, 1),
            inputs={"net_proceeds": 100_000.0},
        )

        assert life_event.event_type == "business_sale"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 1

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="business_sale",
            occurred_on=date.today(),
            inputs={"net_proceeds": 50_000.0},
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
            "event_type": "business_sale",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _BusinessSaleThenFailHandler:
    def __init__(self) -> None:
        self._real = BusinessSaleHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the business sale writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        savings = await _make_liquid_asset(db, user, current_value=15_000.0)
        liability = await _make_business_liability(db, user, balance=25_000.0)
        savings_id = savings.id
        liability_id = liability.id
        user_id = user.id
        await db.commit()

        life_event_service.register_handler(
            "business_sale_then_fail", _BusinessSaleThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="business_sale_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "net_proceeds": 150_000.0,
                        "proceeds_asset_id": str(savings_id),
                        "business_liability_id": str(liability_id),
                        "income_amount": 12_000.0,
                        "new_employment_status": "employed",
                    },
                )

            await db.rollback()

            reloaded_savings = await db.get(Asset, savings_id)
            assert reloaded_savings is not None
            assert reloaded_savings.current_value == 15_000.0

            reloaded_liability = await db.get(Liability, liability_id)
            assert reloaded_liability is not None
            assert reloaded_liability.is_active is True

            result = await db.execute(select(IncomeSource).where(IncomeSource.user_id == user_id))
            assert result.scalars().all() == []

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("business_sale_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reverses_all_effects(self, db: AsyncSession, user: User):
        savings = await _make_liquid_asset(db, user, current_value=15_000.0)
        liability = await _make_business_liability(db, user, balance=25_000.0)
        db.add(UserProfile(user_id=user.id, employment_status="self_employed"))
        await db.flush()

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="business_sale",
            occurred_on=date.today(),
            inputs={
                "net_proceeds": 150_000.0,
                "proceeds_asset_id": str(savings.id),
                "business_liability_id": str(liability.id),
                "income_amount": 12_000.0,
                "new_employment_status": "employed",
            },
        )
        income_id = life_event.effects[2].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False

        await db.refresh(savings)
        assert savings.current_value == 15_000.0

        await db.refresh(liability)
        assert liability.is_active is True

        income = await db.get(IncomeSource, income_id)
        assert income is not None and income.is_active is False

        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        assert profile_result.scalar_one().employment_status == "self_employed"

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="business_sale",
            occurred_on=date.today(),
            inputs={"net_proceeds": 50_000.0},
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

    async def test_undo_blocked_if_the_asset_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="business_sale",
            occurred_on=date.today(),
            inputs={"net_proceeds": 50_000.0},
        )
        asset_id = life_event.effects[0].entity_id

        asset = await db.get(Asset, asset_id)
        assert asset is not None
        asset.current_value = 999_999.0
        db.add(asset)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert any(c.entity_table == "assets" for c in result.conflicts)

    async def test_cannot_undo_another_users_business_sale(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="business_sale",
            occurred_on=date.today(),
            inputs={"net_proceeds": 50_000.0},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_net_worth_and_liabilities_reflect_the_sale(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_business_liability(db, user, balance=30_000.0)

        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="business_sale",
            occurred_on=date.today(),
            inputs={"net_proceeds": 200_000.0, "business_liability_id": str(liability.id)},
        )

        after = await planning_service.get_dashboard(db, user)
        assert after.liabilities == before.liabilities - 30_000.0
        assert after.net_worth == before.net_worth + 200_000.0 + 30_000.0

    async def test_high_interest_debt_recommendation_stops_firing_after_the_sale(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_business_liability(db, user, balance=20_000.0)
        liability.interest_rate = 0.18
        db.add(liability)
        await db.flush()
        household, _created = await family_service.get_or_create_household(db, user)

        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "high_interest_debt" for r in before_recs)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="business_sale",
            occurred_on=date.today(),
            inputs={"net_proceeds": 100_000.0, "business_liability_id": str(liability.id)},
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "high_interest_debt" for r in after_recs)
