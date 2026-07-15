"""Life Event Engine — Inheritance (LifeEventEngineArchitecture.md §5.11).

Covers the handler in isolation (asset-only and asset+linked-income
paths), the full record/undo workflow through the generic engine, a
rollback proof, and verification that the live Recommendation Engine
reflects the change with zero new calculation logic of their own.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import Asset, IncomeSource, Liability
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import family_service, life_event_service
from app.services.family_recommendations_service import get_family_recommendations
from app.services.inheritance_handler import InheritanceHandler
from app.services.life_event_service import EntityEffect

# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestInheritanceHandlerUnit:
    async def test_apply_creates_a_savings_asset_by_default(
        self, db: AsyncSession, user: User
    ):
        effects = await InheritanceHandler().apply(db, user, {"amount": 50_000.0})

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "assets"
        assert effect.change_type == "create"
        assert effect.before_state is None
        assert effect.after_state["current_value"] == 50_000.0
        assert effect.after_state["asset_type"] == "savings"

        result = await db.execute(select(Asset).where(Asset.user_id == user.id))
        asset = result.scalar_one()
        assert asset.description == "Inheritance"

    async def test_apply_honors_an_explicit_asset_type(self, db: AsyncSession, user: User):
        effects = await InheritanceHandler().apply(
            db,
            user,
            {"amount": 300_000.0, "asset_type": "real_estate", "description": "Family home"},
        )

        assert effects[0].after_state["asset_type"] == "real_estate"
        result = await db.execute(select(Asset).where(Asset.user_id == user.id))
        assert result.scalar_one().description == "Family home"

    async def test_apply_also_creates_the_linked_income_source(
        self, db: AsyncSession, user: User
    ):
        effects = await InheritanceHandler().apply(
            db,
            user,
            {
                "amount": 400_000.0,
                "asset_type": "real_estate",
                "income_amount": 24_000.0,
            },
        )

        assert len(effects) == 2
        asset_effect, income_effect = effects
        assert asset_effect.entity_table == "assets"
        assert income_effect.entity_table == "income_sources"
        assert income_effect.change_type == "create"
        assert income_effect.after_state["source_type"] == "rental"
        assert income_effect.after_state["annual_amount"] == 24_000.0

        result = await db.execute(select(IncomeSource).where(IncomeSource.user_id == user.id))
        income = result.scalar_one()
        assert income.description == "Inherited income"

    async def test_apply_honors_an_explicit_income_source_type(
        self, db: AsyncSession, user: User
    ):
        effects = await InheritanceHandler().apply(
            db,
            user,
            {
                "amount": 100_000.0,
                "asset_type": "brokerage",
                "income_amount": 5_000.0,
                "income_source_type": "investment",
            },
        )

        assert effects[1].after_state["source_type"] == "investment"

    async def test_apply_ignores_income_amount_absent_by_default(
        self, db: AsyncSession, user: User
    ):
        effects = await InheritanceHandler().apply(db, user, {"amount": 20_000.0})

        assert len(effects) == 1
        result = await db.execute(select(IncomeSource).where(IncomeSource.user_id == user.id))
        assert result.scalars().all() == []


# ── Integration: the full workflow through the generic engine ──────────────


class TestInheritanceFullWorkflow:
    async def test_records_life_event_and_effect_and_creates_the_asset(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="inheritance",
            occurred_on=date(2026, 10, 1),
            inputs={"amount": 60_000.0},
        )

        assert life_event.event_type == "inheritance"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 1

    async def test_records_both_effects_when_income_is_linked(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="inheritance",
            occurred_on=date.today(),
            inputs={"amount": 350_000.0, "asset_type": "real_estate", "income_amount": 18_000.0},
        )

        assert len(life_event.effects) == 2
        tables = {e.entity_table for e in life_event.effects}
        assert tables == {"assets", "income_sources"}

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="inheritance",
            occurred_on=date.today(),
            inputs={"amount": 10_000.0},
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
            "event_type": "inheritance",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _InheritanceThenFailHandler:
    def __init__(self) -> None:
        self._real = InheritanceHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the asset/income writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        user_id = user.id
        await db.commit()
        life_event_service.register_handler(
            "inheritance_then_fail", _InheritanceThenFailHandler()
        )
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="inheritance_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "amount": 250_000.0,
                        "asset_type": "real_estate",
                        "income_amount": 15_000.0,
                    },
                )

            await db.rollback()

            result = await db.execute(select(Asset).where(Asset.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(select(IncomeSource).where(IncomeSource.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("inheritance_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_soft_deletes_both_created_rows(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="inheritance",
            occurred_on=date.today(),
            inputs={"amount": 300_000.0, "asset_type": "real_estate", "income_amount": 20_000.0},
        )
        asset_id = life_event.effects[0].entity_id
        income_id = life_event.effects[1].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        asset = await db.get(Asset, asset_id)
        income = await db.get(IncomeSource, income_id)
        assert asset is not None and asset.is_active is False
        assert income is not None and income.is_active is False

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="inheritance", occurred_on=date.today(), inputs={"amount": 5_000.0}
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
            event_type="inheritance",
            occurred_on=date.today(),
            inputs={"amount": 40_000.0},
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

    async def test_cannot_undo_another_users_inheritance(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db, user, event_type="inheritance", occurred_on=date.today(), inputs={"amount": 5_000.0}
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Recommendation verification ─────────────────────────────────────────────


class TestRecommendationIntegration:
    async def test_negative_net_worth_trend_stops_firing_after_an_inheritance(
        self, db: AsyncSession, user: User
    ):
        db.add(
            Liability(
                user_id=user.id,
                liability_type="personal_loan",
                balance=40_000.0,
                monthly_payment=500.0,
            )
        )
        await db.flush()
        household, _created = await family_service.get_or_create_household(db, user)

        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "negative_net_worth_trend" for r in before_recs)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="inheritance",
            occurred_on=date.today(),
            inputs={"amount": 100_000.0},
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "negative_net_worth_trend" for r in after_recs)
