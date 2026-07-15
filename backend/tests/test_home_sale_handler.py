"""Life Event Engine — Home Sale (LifeEventEngineArchitecture.md §5.8).

Covers the handler in isolation (proceeds-to-new-asset and
proceeds-to-existing-asset paths, with and without a linked mortgage
payoff), the full record/undo workflow through the generic engine, a
rollback proof, and verification that Dashboard and the live
Recommendation Engine reflect the change with zero new calculation logic
of their own.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import Asset, Liability
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import family_service, life_event_service, planning_service
from app.services.family_recommendations_service import get_family_recommendations
from app.services.home_sale_handler import HomeSaleHandler


async def _make_home(db: AsyncSession, user: User, *, current_value: float = 400_000.0) -> Asset:
    asset = Asset(user_id=user.id, asset_type="real_estate", current_value=current_value)
    db.add(asset)
    await db.flush()
    return asset


async def _make_mortgage(
    db: AsyncSession, user: User, *, balance: float = 300_000.0
) -> Liability:
    liability = Liability(
        user_id=user.id,
        liability_type="mortgage",
        balance=balance,
        interest_rate=0.06,
        monthly_payment=1_800.0,
    )
    db.add(liability)
    await db.flush()
    return liability


async def _make_liquid_asset(
    db: AsyncSession, user: User, *, current_value: float = 10_000.0
) -> Asset:
    asset = Asset(user_id=user.id, asset_type="savings", current_value=current_value)
    db.add(asset)
    await db.flush()
    return asset


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestHomeSaleHandlerUnit:
    async def test_apply_sells_home_pays_off_mortgage_and_creates_a_new_proceeds_asset(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user, current_value=450_000.0)
        mortgage = await _make_mortgage(db, user, balance=300_000.0)

        effects = await HomeSaleHandler().apply(
            db,
            user,
            {
                "home_asset_id": str(home.id),
                "mortgage_liability_id": str(mortgage.id),
                "net_proceeds": 140_000.0,
            },
        )

        assert len(effects) == 3
        home_effect, mortgage_effect, proceeds_effect = effects
        assert home_effect.entity_table == "assets"
        assert home_effect.change_type == "soft_delete"
        assert home_effect.after_state["is_active"] is False

        assert mortgage_effect.entity_table == "liabilities"
        assert mortgage_effect.change_type == "soft_delete"
        assert mortgage_effect.after_state["is_active"] is False

        assert proceeds_effect.entity_table == "assets"
        assert proceeds_effect.change_type == "create"
        assert proceeds_effect.after_state["current_value"] == 140_000.0

        await db.refresh(home)
        assert home.is_active is False
        await db.refresh(mortgage)
        assert mortgage.is_active is False

    async def test_apply_adds_proceeds_to_an_existing_liquid_asset(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user)
        savings = await _make_liquid_asset(db, user, current_value=20_000.0)

        effects = await HomeSaleHandler().apply(
            db,
            user,
            {
                "home_asset_id": str(home.id),
                "net_proceeds": 100_000.0,
                "proceeds_asset_id": str(savings.id),
            },
        )

        assert len(effects) == 2
        proceeds_effect = effects[1]
        assert proceeds_effect.change_type == "update"
        assert proceeds_effect.before_state["current_value"] == 20_000.0
        assert proceeds_effect.after_state["current_value"] == 120_000.0

        await db.refresh(savings)
        assert savings.current_value == 120_000.0

    async def test_apply_leaves_the_mortgage_untouched_when_payoff_mortgage_is_false(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user)
        mortgage = await _make_mortgage(db, user)

        effects = await HomeSaleHandler().apply(
            db,
            user,
            {
                "home_asset_id": str(home.id),
                "mortgage_liability_id": str(mortgage.id),
                "payoff_mortgage": False,
                "net_proceeds": 50_000.0,
            },
        )

        assert len(effects) == 2  # home + new proceeds asset, no liability effect
        await db.refresh(mortgage)
        assert mortgage.is_active is True

    async def test_apply_without_a_mortgage_creates_only_two_effects(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user)

        effects = await HomeSaleHandler().apply(
            db, user, {"home_asset_id": str(home.id), "net_proceeds": 300_000.0}
        )

        assert len(effects) == 2
        assert [e.entity_table for e in effects] == ["assets", "assets"]

    async def test_apply_raises_for_a_nonexistent_home_asset(
        self, db: AsyncSession, user: User
    ):
        from uuid import uuid4

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await HomeSaleHandler().apply(
                db, user, {"home_asset_id": str(uuid4()), "net_proceeds": 100_000.0}
            )
        assert exc_info.value.status_code == 404


# ── Integration: the full workflow through the generic engine ──────────────


class TestHomeSaleFullWorkflow:
    async def test_records_life_event_and_all_effects(self, db: AsyncSession, user: User):
        home = await _make_home(db, user)
        mortgage = await _make_mortgage(db, user)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="home_sale",
            occurred_on=date(2026, 9, 1),
            inputs={
                "home_asset_id": str(home.id),
                "mortgage_liability_id": str(mortgage.id),
                "net_proceeds": 120_000.0,
            },
        )

        assert life_event.event_type == "home_sale"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 3

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        home = await _make_home(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="home_sale",
            occurred_on=date.today(),
            inputs={"home_asset_id": str(home.id), "net_proceeds": 250_000.0},
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
            "event_type": "home_sale",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _HomeSaleThenFailHandler:
    def __init__(self) -> None:
        self._real = HomeSaleHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the home sale writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user, current_value=400_000.0)
        mortgage = await _make_mortgage(db, user, balance=300_000.0)
        savings = await _make_liquid_asset(db, user, current_value=15_000.0)
        home_id = home.id
        mortgage_id = mortgage.id
        savings_id = savings.id
        user_id = user.id
        await db.commit()

        life_event_service.register_handler("home_sale_then_fail", _HomeSaleThenFailHandler())
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="home_sale_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "home_asset_id": str(home_id),
                        "mortgage_liability_id": str(mortgage_id),
                        "proceeds_asset_id": str(savings_id),
                        "net_proceeds": 130_000.0,
                    },
                )

            await db.rollback()

            reloaded_home = await db.get(Asset, home_id)
            assert reloaded_home is not None
            assert reloaded_home.is_active is True

            reloaded_mortgage = await db.get(Liability, mortgage_id)
            assert reloaded_mortgage is not None
            assert reloaded_mortgage.is_active is True

            reloaded_savings = await db.get(Asset, savings_id)
            assert reloaded_savings is not None
            assert reloaded_savings.current_value == 15_000.0

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("home_sale_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reverses_all_three_effects(self, db: AsyncSession, user: User):
        home = await _make_home(db, user)
        mortgage = await _make_mortgage(db, user, balance=280_000.0)
        savings = await _make_liquid_asset(db, user, current_value=25_000.0)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="home_sale",
            occurred_on=date.today(),
            inputs={
                "home_asset_id": str(home.id),
                "mortgage_liability_id": str(mortgage.id),
                "proceeds_asset_id": str(savings.id),
                "net_proceeds": 120_000.0,
            },
        )

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False

        await db.refresh(home)
        assert home.is_active is True
        await db.refresh(mortgage)
        assert mortgage.is_active is True
        assert mortgage.balance == 280_000.0
        await db.refresh(savings)
        assert savings.current_value == 25_000.0

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="home_sale",
            occurred_on=date.today(),
            inputs={"home_asset_id": str(home.id), "net_proceeds": 200_000.0},
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

    async def test_undo_blocked_if_the_home_asset_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="home_sale",
            occurred_on=date.today(),
            inputs={"home_asset_id": str(home.id), "net_proceeds": 200_000.0},
        )

        home.current_value = 999_999.0
        db.add(home)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert any(c.entity_table == "assets" for c in result.conflicts)

    async def test_cannot_undo_another_users_home_sale(
        self, db: AsyncSession, user: User, other_user: User
    ):
        home = await _make_home(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="home_sale",
            occurred_on=date.today(),
            inputs={"home_asset_id": str(home.id), "net_proceeds": 200_000.0},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_net_worth_and_liabilities_reflect_the_sale(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user, current_value=400_000.0)
        mortgage = await _make_mortgage(db, user, balance=300_000.0)

        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="home_sale",
            occurred_on=date.today(),
            inputs={
                "home_asset_id": str(home.id),
                "mortgage_liability_id": str(mortgage.id),
                "net_proceeds": 130_000.0,
            },
        )

        after = await planning_service.get_dashboard(db, user)
        assert after.liabilities == before.liabilities - 300_000.0
        # Net worth: -400k home, +300k mortgage cleared, +130k proceeds = +30k
        assert after.net_worth == before.net_worth + 30_000.0

    async def test_high_interest_debt_recommendation_stops_firing_after_the_sale(
        self, db: AsyncSession, user: User
    ):
        home = await _make_home(db, user)
        mortgage = await _make_mortgage(db, user, balance=250_000.0)
        household, _created = await family_service.get_or_create_household(db, user)

        # Bump the mortgage rate above the high-interest threshold directly.
        mortgage.interest_rate = 0.15
        db.add(mortgage)
        await db.flush()

        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "high_interest_debt" for r in before_recs)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="home_sale",
            occurred_on=date.today(),
            inputs={
                "home_asset_id": str(home.id),
                "mortgage_liability_id": str(mortgage.id),
                "net_proceeds": 100_000.0,
            },
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "high_interest_debt" for r in after_recs)
