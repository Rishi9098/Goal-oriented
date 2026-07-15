"""Life Event Engine — New Loan (LifeEventEngineArchitecture.md §5.9).

Covers the handler in isolation (loan-only and loan+linked-asset paths),
the full record/undo workflow through the generic engine, a rollback
proof, and verification that Dashboard and the live Recommendation Engine
reflect the new liability with zero new calculation logic of their own.
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
from app.services.life_event_service import EntityEffect
from app.services.new_loan_handler import NewLoanHandler

# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestNewLoanHandlerUnit:
    async def test_apply_creates_a_liability_only_when_no_asset_is_linked(
        self, db: AsyncSession, user: User
    ):
        effects = await NewLoanHandler().apply(
            db,
            user,
            {
                "liability_type": "auto_loan",
                "balance": 25_000.0,
                "interest_rate": 0.06,
                "monthly_payment": 450.0,
            },
        )

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "liabilities"
        assert effect.change_type == "create"
        assert effect.before_state is None
        assert effect.after_state["balance"] == 25_000.0
        assert effect.after_state["interest_rate"] == 0.06

        result = await db.execute(select(Liability).where(Liability.user_id == user.id))
        liability = result.scalar_one()
        assert liability.liability_type == "auto_loan"
        assert liability.monthly_payment == 450.0
        assert liability.is_active is True

    async def test_apply_also_creates_the_linked_asset_when_both_fields_are_given(
        self, db: AsyncSession, user: User
    ):
        effects = await NewLoanHandler().apply(
            db,
            user,
            {
                "liability_type": "auto_loan",
                "balance": 22_000.0,
                "monthly_payment": 400.0,
                "asset_type": "vehicle",
                "asset_value": 24_000.0,
                "asset_description": "New car",
            },
        )

        assert len(effects) == 2
        liability_effect, asset_effect = effects
        assert liability_effect.entity_table == "liabilities"
        assert asset_effect.entity_table == "assets"
        assert asset_effect.change_type == "create"
        assert asset_effect.after_state["current_value"] == 24_000.0

        result = await db.execute(select(Asset).where(Asset.user_id == user.id))
        asset = result.scalar_one()
        assert asset.asset_type == "vehicle"
        assert asset.description == "New car"

    async def test_apply_ignores_asset_type_when_asset_value_is_absent(
        self, db: AsyncSession, user: User
    ):
        """Explicit opt-in required for the linked-purchase step — an
        asset_type with no accompanying asset_value must not create an
        asset at all."""
        effects = await NewLoanHandler().apply(
            db,
            user,
            {
                "liability_type": "personal_loan",
                "balance": 5_000.0,
                "monthly_payment": 200.0,
                "asset_type": "vehicle",
            },
        )

        assert len(effects) == 1
        result = await db.execute(select(Asset).where(Asset.user_id == user.id))
        assert result.scalars().all() == []

    async def test_apply_defaults_monthly_payment_and_allows_no_interest_rate(
        self, db: AsyncSession, user: User
    ):
        effects = await NewLoanHandler().apply(
            db, user, {"liability_type": "other", "balance": 1_000.0}
        )

        assert effects[0].after_state["interest_rate"] is None
        result = await db.execute(select(Liability).where(Liability.user_id == user.id))
        assert result.scalar_one().monthly_payment == 0.0


# ── Integration: the full workflow through the generic engine ──────────────


class TestNewLoanFullWorkflow:
    async def test_records_life_event_and_effect_and_creates_the_liability(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date(2026, 7, 1),
            inputs={
                "liability_type": "credit_card",
                "balance": 3_000.0,
                "interest_rate": 0.24,
                "monthly_payment": 150.0,
            },
        )

        assert life_event.event_type == "new_loan"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 1

        result = await db.execute(select(Liability).where(Liability.user_id == user.id))
        assert result.scalar_one().balance == 3_000.0

    async def test_records_both_effects_when_an_asset_is_linked(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={
                "liability_type": "auto_loan",
                "balance": 18_000.0,
                "monthly_payment": 350.0,
                "asset_type": "vehicle",
                "asset_value": 20_000.0,
            },
        )

        assert len(life_event.effects) == 2
        tables = {effect.entity_table for effect in life_event.effects}
        assert tables == {"liabilities", "assets"}

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={"liability_type": "student_loan", "balance": 10_000.0},
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
            "event_type": "new_loan",
        }


# ── Rollback: a failure after the write must leave nothing durable ─────────


class _NewLoanThenFailHandler:
    def __init__(self) -> None:
        self._real = NewLoanHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the liability/asset writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        user_id = user.id
        await db.commit()
        life_event_service.register_handler("new_loan_then_fail", _NewLoanThenFailHandler())
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="new_loan_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "liability_type": "auto_loan",
                        "balance": 30_000.0,
                        "monthly_payment": 500.0,
                        "asset_type": "vehicle",
                        "asset_value": 32_000.0,
                    },
                )

            await db.rollback()

            result = await db.execute(select(Liability).where(Liability.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(select(Asset).where(Asset.user_id == user_id))
            assert result.scalars().all() == []

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(
                select(AuditLog).where(
                    AuditLog.user_id == user_id, AuditLog.action == "life_event_recorded"
                )
            )
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("new_loan_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_soft_deletes_the_liability_only_when_no_asset_was_linked(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={"liability_type": "personal_loan", "balance": 4_000.0},
        )
        liability_id = life_event.effects[0].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        liability = await db.get(Liability, liability_id)
        assert liability is not None
        assert liability.is_active is False

        await db.refresh(life_event)
        assert life_event.status == "undone"

    async def test_undo_soft_deletes_both_liability_and_linked_asset(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={
                "liability_type": "auto_loan",
                "balance": 18_000.0,
                "monthly_payment": 350.0,
                "asset_type": "vehicle",
                "asset_value": 20_000.0,
            },
        )
        liability_id = life_event.effects[0].entity_id
        asset_id = life_event.effects[1].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        liability = await db.get(Liability, liability_id)
        asset = await db.get(Asset, asset_id)
        assert liability is not None and liability.is_active is False
        assert asset is not None and asset.is_active is False

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={"liability_type": "other", "balance": 1_500.0},
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

    async def test_undo_blocked_if_the_liability_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={"liability_type": "credit_card", "balance": 2_000.0},
        )
        liability_id = life_event.effects[0].entity_id

        liability = await db.get(Liability, liability_id)
        assert liability is not None
        liability.balance = 999_999.0
        db.add(liability)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert len(result.conflicts) == 1
        assert result.conflicts[0].entity_table == "liabilities"

    async def test_cannot_undo_another_users_new_loan(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={"liability_type": "other", "balance": 500.0},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_liabilities_and_net_worth_reflect_the_new_loan(
        self, db: AsyncSession, user: User
    ):
        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={"liability_type": "auto_loan", "balance": 15_000.0, "monthly_payment": 300.0},
        )

        after = await planning_service.get_dashboard(db, user)
        assert after.liabilities == before.liabilities + 15_000.0
        assert after.net_worth == before.net_worth - 15_000.0

    async def test_high_interest_debt_recommendation_fires_immediately_for_a_high_rate_loan(
        self, db: AsyncSession, user: User
    ):
        household, _created = await family_service.get_or_create_household(db, user)

        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "high_interest_debt" for r in before_recs)

        # 24% is above family_recommendations_service's own
        # _HIGH_INTEREST_THRESHOLD (0.10) — reused, not restated.
        await life_event_service.record_life_event(
            db,
            user,
            event_type="new_loan",
            occurred_on=date.today(),
            inputs={
                "liability_type": "credit_card",
                "balance": 6_000.0,
                "interest_rate": 0.24,
                "monthly_payment": 200.0,
            },
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "high_interest_debt" for r in after_recs)
