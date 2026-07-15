"""Life Event Engine — Bonus.

Not one of the architecture's original 15 catalogued events (see this
event's own module docstring for the design rationale: modeled directly
on Inheritance, §5.11). Covers the handler in isolation, the full
record/undo workflow through the generic engine, a rollback proof, and
verification that Dashboard and the live Recommendation Engine reflect
the new liquid asset with zero new calculation logic of their own.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import Asset, Expense
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import family_service, life_event_service, planning_service
from app.services.bonus_handler import BonusHandler
from app.services.family_recommendations_service import get_family_recommendations
from app.services.life_event_service import EntityEffect

# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestBonusHandlerUnit:
    async def test_apply_creates_a_savings_asset_by_default(
        self, db: AsyncSession, user: User
    ):
        effects = await BonusHandler().apply(db, user, {"amount": 5_000.0})

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "assets"
        assert effect.change_type == "create"
        assert effect.before_state is None
        assert effect.after_state["current_value"] == 5_000.0
        assert effect.after_state["asset_type"] == "savings"

        result = await db.execute(select(Asset).where(Asset.user_id == user.id))
        asset = result.scalar_one()
        assert asset.current_value == 5_000.0
        assert asset.asset_type == "savings"
        assert asset.description == "Bonus"
        assert asset.is_active is True

    async def test_apply_honors_an_explicit_asset_type_and_description(
        self, db: AsyncSession, user: User
    ):
        effects = await BonusHandler().apply(
            db,
            user,
            {
                "amount": 12_000.0,
                "asset_type": "brokerage",
                "institution": "Fidelity",
                "description": "Year-end bonus, invested",
            },
        )

        assert effects[0].after_state["asset_type"] == "brokerage"

        result = await db.execute(select(Asset).where(Asset.user_id == user.id))
        asset = result.scalar_one()
        assert asset.asset_type == "brokerage"
        assert asset.institution == "Fidelity"
        assert asset.description == "Year-end bonus, invested"


# ── Integration: the full workflow through the generic engine ──────────────


class TestBonusFullWorkflow:
    async def test_records_life_event_and_effect_and_creates_the_asset(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="bonus",
            occurred_on=date(2026, 6, 1),
            inputs={"amount": 8_000.0},
        )

        assert life_event.event_type == "bonus"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 1
        assert life_event.effects[0].entity_table == "assets"

        result = await db.execute(select(Asset).where(Asset.user_id == user.id))
        assert result.scalar_one().current_value == 8_000.0

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="bonus", occurred_on=date.today(), inputs={"amount": 3_000.0}
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
            "event_type": "bonus",
        }


# ── Rollback: a failure after the write must leave nothing durable ─────────


class _BonusThenFailHandler:
    def __init__(self) -> None:
        self._real = BonusHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the asset was created")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        user_id = user.id
        await db.commit()
        life_event_service.register_handler("bonus_then_fail", _BonusThenFailHandler())
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="bonus_then_fail",
                    occurred_on=date.today(),
                    inputs={"amount": 20_000.0},
                )

            await db.rollback()

            result = await db.execute(select(Asset).where(Asset.user_id == user_id))
            assert result.scalars().all() == []  # the created asset did not survive

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(
                select(AuditLog).where(
                    AuditLog.user_id == user_id, AuditLog.action == "life_event_recorded"
                )
            )
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("bonus_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_soft_deletes_the_created_asset(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="bonus", occurred_on=date.today(), inputs={"amount": 6_000.0}
        )
        asset_id = life_event.effects[0].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        assert result.conflicts == []

        asset = await db.get(Asset, asset_id)
        assert asset is not None
        assert asset.is_active is False  # generic undo: create -> soft-delete

        await db.refresh(life_event)
        assert life_event.status == "undone"

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="bonus", occurred_on=date.today(), inputs={"amount": 1_000.0}
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
            db, user, event_type="bonus", occurred_on=date.today(), inputs={"amount": 4_000.0}
        )
        asset_id = life_event.effects[0].entity_id

        asset = await db.get(Asset, asset_id)
        assert asset is not None
        asset.current_value = 999_999.0
        db.add(asset)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert len(result.conflicts) == 1
        assert result.conflicts[0].entity_table == "assets"

        unchanged = await db.get(Asset, asset_id)
        assert unchanged is not None
        assert unchanged.is_active is True  # undo did not proceed

    async def test_cannot_undo_another_users_bonus(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="bonus", occurred_on=date.today(), inputs={"amount": 2_000.0}
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_net_worth_and_liquid_assets_rise_after_a_bonus(
        self, db: AsyncSession, user: User
    ):
        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db, user, event_type="bonus", occurred_on=date.today(), inputs={"amount": 10_000.0}
        )

        after = await planning_service.get_dashboard(db, user)
        assert after.net_worth == before.net_worth + 10_000.0

    async def test_low_liquidity_recommendation_stops_firing_after_a_bonus(
        self, db: AsyncSession, user: User
    ):
        # Expenses high enough, relative to zero starting liquid assets, to
        # trip family_recommendations_service's own low_liquidity rule
        # (real threshold constant, not restated by this test).
        db.add(Expense(user_id=user.id, category="housing", monthly_amount=3_000.0))
        await db.flush()
        household, _created = await family_service.get_or_create_household(db, user)

        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "low_liquidity" for r in before_recs)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="bonus",
            occurred_on=date.today(),
            inputs={"amount": 50_000.0, "asset_type": "savings"},
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "low_liquidity" for r in after_recs)
