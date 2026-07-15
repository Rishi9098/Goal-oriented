"""Life Event Engine — House Purchase (LifeEventEngineArchitecture.md §5.7).

Covers the handler in isolation (base, down-payment, and linked-goal
paths), the full record/undo workflow through the generic engine, a
rollback proof across up to four entities, and verification that
Dashboard and the live Recommendation Engine reflect the change with zero
new calculation logic of their own.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import Asset, Liability
from app.models.goal import Goal
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import family_service, life_event_service, planning_service
from app.services.family_recommendations_service import get_family_recommendations
from app.services.house_purchase_handler import HousePurchaseHandler


async def _make_liquid_asset(
    db: AsyncSession, user: User, *, current_value: float = 50_000.0
) -> Asset:
    asset = Asset(user_id=user.id, asset_type="savings", current_value=current_value)
    db.add(asset)
    await db.flush()
    return asset


async def _make_goal(
    db: AsyncSession, user: User, *, current_amount: float = 10_000.0
) -> Goal:
    goal = Goal(
        user_id=user.id,
        name="Home Purchase",
        category="home",
        target_amount=100_000.0,
        current_amount=current_amount,
        target_date=date.today() + timedelta(days=365 * 3),
        monthly_contribution=500.0,
        risk_profile="balanced",
    )
    await planning_service.calculate_goal_probability(goal)
    db.add(goal)
    await db.flush()
    return goal


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestHousePurchaseHandlerUnit:
    async def test_apply_creates_home_asset_and_mortgage_liability_only(
        self, db: AsyncSession, user: User
    ):
        effects = await HousePurchaseHandler().apply(
            db,
            user,
            {
                "property_value": 400_000.0,
                "mortgage_balance": 320_000.0,
                "mortgage_interest_rate": 0.065,
                "mortgage_monthly_payment": 2_100.0,
            },
        )

        assert len(effects) == 2
        asset_effect, liability_effect = effects
        assert asset_effect.entity_table == "assets"
        assert asset_effect.change_type == "create"
        assert asset_effect.after_state["asset_type"] == "real_estate"
        assert asset_effect.after_state["current_value"] == 400_000.0

        assert liability_effect.entity_table == "liabilities"
        assert liability_effect.change_type == "create"
        assert liability_effect.after_state["balance"] == 320_000.0

        result = await db.execute(select(Liability).where(Liability.user_id == user.id))
        assert result.scalar_one().liability_type == "mortgage"

    async def test_apply_also_reduces_the_down_payment_asset(
        self, db: AsyncSession, user: User
    ):
        funding_asset = await _make_liquid_asset(db, user, current_value=80_000.0)

        effects = await HousePurchaseHandler().apply(
            db,
            user,
            {
                "property_value": 400_000.0,
                "mortgage_balance": 340_000.0,
                "down_payment_asset_id": str(funding_asset.id),
                "down_payment_amount": 60_000.0,
            },
        )

        assert len(effects) == 3
        down_payment_effect = effects[2]
        assert down_payment_effect.entity_table == "assets"
        assert down_payment_effect.entity_id == funding_asset.id
        assert down_payment_effect.change_type == "update"
        assert down_payment_effect.before_state["current_value"] == 80_000.0
        assert down_payment_effect.after_state["current_value"] == 20_000.0

        await db.refresh(funding_asset)
        assert funding_asset.current_value == 20_000.0

    async def test_apply_also_updates_a_linked_goals_current_amount(
        self, db: AsyncSession, user: User
    ):
        goal = await _make_goal(db, user, current_amount=10_000.0)

        effects = await HousePurchaseHandler().apply(
            db,
            user,
            {
                "property_value": 400_000.0,
                "mortgage_balance": 340_000.0,
                "goal_id": str(goal.id),
                "new_goal_current_amount": 60_000.0,
            },
        )

        assert len(effects) == 3
        goal_effect = effects[2]
        assert goal_effect.entity_table == "goals"
        assert goal_effect.before_state["current_amount"] == 10_000.0
        assert goal_effect.after_state["current_amount"] == 60_000.0
        # current_amount is in CALCULATION_CONTEXT_FIELDS
        assert "probability" in goal_effect.after_state

        await db.refresh(goal)
        assert goal.current_amount == 60_000.0

    async def test_apply_ignores_down_payment_asset_id_without_an_amount(
        self, db: AsyncSession, user: User
    ):
        funding_asset = await _make_liquid_asset(db, user, current_value=80_000.0)

        effects = await HousePurchaseHandler().apply(
            db,
            user,
            {
                "property_value": 400_000.0,
                "mortgage_balance": 340_000.0,
                "down_payment_asset_id": str(funding_asset.id),
            },
        )

        assert len(effects) == 2
        await db.refresh(funding_asset)
        assert funding_asset.current_value == 80_000.0

    async def test_apply_all_four_effects_together(self, db: AsyncSession, user: User):
        funding_asset = await _make_liquid_asset(db, user, current_value=80_000.0)
        goal = await _make_goal(db, user, current_amount=10_000.0)

        effects = await HousePurchaseHandler().apply(
            db,
            user,
            {
                "property_value": 400_000.0,
                "mortgage_balance": 340_000.0,
                "down_payment_asset_id": str(funding_asset.id),
                "down_payment_amount": 60_000.0,
                "goal_id": str(goal.id),
                "new_goal_current_amount": 60_000.0,
            },
        )

        assert len(effects) == 4
        assert [e.entity_table for e in effects] == [
            "assets",
            "liabilities",
            "assets",
            "goals",
        ]

    async def test_apply_raises_for_a_nonexistent_down_payment_asset(
        self, db: AsyncSession, user: User
    ):
        from uuid import uuid4

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await HousePurchaseHandler().apply(
                db,
                user,
                {
                    "property_value": 400_000.0,
                    "mortgage_balance": 340_000.0,
                    "down_payment_asset_id": str(uuid4()),
                    "down_payment_amount": 20_000.0,
                },
            )
        assert exc_info.value.status_code == 404


# ── Integration: the full workflow through the generic engine ──────────────


class TestHousePurchaseFullWorkflow:
    async def test_records_life_event_and_base_effects(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="house_purchase",
            occurred_on=date(2026, 8, 1),
            inputs={"property_value": 350_000.0, "mortgage_balance": 300_000.0},
        )

        assert life_event.event_type == "house_purchase"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 2

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="house_purchase",
            occurred_on=date.today(),
            inputs={"property_value": 350_000.0, "mortgage_balance": 300_000.0},
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
            "event_type": "house_purchase",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _HousePurchaseThenFailHandler:
    def __init__(self) -> None:
        self._real = HousePurchaseHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the house purchase writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        funding_asset = await _make_liquid_asset(db, user, current_value=80_000.0)
        goal = await _make_goal(db, user, current_amount=10_000.0)
        funding_asset_id = funding_asset.id
        goal_id = goal.id
        user_id = user.id
        await db.commit()

        life_event_service.register_handler(
            "house_purchase_then_fail", _HousePurchaseThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="house_purchase_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "property_value": 400_000.0,
                        "mortgage_balance": 340_000.0,
                        "down_payment_asset_id": str(funding_asset_id),
                        "down_payment_amount": 60_000.0,
                        "goal_id": str(goal_id),
                        "new_goal_current_amount": 60_000.0,
                    },
                )

            await db.rollback()

            result = await db.execute(
                select(Asset).where(Asset.user_id == user_id, Asset.asset_type == "real_estate")
            )
            assert result.scalars().all() == []
            result = await db.execute(select(Liability).where(Liability.user_id == user_id))
            assert result.scalars().all() == []

            reloaded_funding_asset = await db.get(Asset, funding_asset_id)
            assert reloaded_funding_asset is not None
            assert reloaded_funding_asset.current_value == 80_000.0

            reloaded_goal = await db.get(Goal, goal_id)
            assert reloaded_goal is not None
            assert reloaded_goal.current_amount == 10_000.0

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("house_purchase_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reverses_all_four_effects(self, db: AsyncSession, user: User):
        funding_asset = await _make_liquid_asset(db, user, current_value=80_000.0)
        goal = await _make_goal(db, user, current_amount=10_000.0)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="house_purchase",
            occurred_on=date.today(),
            inputs={
                "property_value": 400_000.0,
                "mortgage_balance": 340_000.0,
                "down_payment_asset_id": str(funding_asset.id),
                "down_payment_amount": 60_000.0,
                "goal_id": str(goal.id),
                "new_goal_current_amount": 60_000.0,
            },
        )
        home_asset_id = life_event.effects[0].entity_id
        liability_id = life_event.effects[1].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False

        home_asset = await db.get(Asset, home_asset_id)
        assert home_asset is not None and home_asset.is_active is False

        liability = await db.get(Liability, liability_id)
        assert liability is not None and liability.is_active is False

        await db.refresh(funding_asset)
        assert funding_asset.current_value == 80_000.0

        await db.refresh(goal)
        assert goal.current_amount == 10_000.0

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="house_purchase",
            occurred_on=date.today(),
            inputs={"property_value": 300_000.0, "mortgage_balance": 250_000.0},
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
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="house_purchase",
            occurred_on=date.today(),
            inputs={"property_value": 300_000.0, "mortgage_balance": 250_000.0},
        )
        home_asset_id = life_event.effects[0].entity_id

        home_asset = await db.get(Asset, home_asset_id)
        assert home_asset is not None
        home_asset.current_value = 999_999.0
        db.add(home_asset)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert any(c.entity_table == "assets" for c in result.conflicts)

    async def test_cannot_undo_another_users_house_purchase(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="house_purchase",
            occurred_on=date.today(),
            inputs={"property_value": 300_000.0, "mortgage_balance": 250_000.0},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_net_worth_reflects_the_purchase(
        self, db: AsyncSession, user: User
    ):
        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="house_purchase",
            occurred_on=date.today(),
            inputs={"property_value": 400_000.0, "mortgage_balance": 340_000.0},
        )

        after = await planning_service.get_dashboard(db, user)
        # Net worth rises by exactly the equity (property value minus new
        # mortgage balance) — proving both the asset and liability writes
        # landed, not just one.
        assert after.net_worth == before.net_worth + 60_000.0

    async def test_high_interest_debt_recommendation_fires_for_a_high_rate_mortgage(
        self, db: AsyncSession, user: User
    ):
        household, _created = await family_service.get_or_create_household(db, user)

        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "high_interest_debt" for r in before_recs)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="house_purchase",
            occurred_on=date.today(),
            inputs={
                "property_value": 400_000.0,
                "mortgage_balance": 340_000.0,
                "mortgage_interest_rate": 0.15,
            },
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "high_interest_debt" for r in after_recs)
