"""Life Event Engine, Phase B.1 — Loan Payoff.

Covers the handler in isolation, the full record/undo workflow through the
generic engine, a rollback proof, and verification that Dashboard and the
live Recommendation Engine reflect the change with zero new calculation
logic of their own.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import Liability
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import family_service, life_event_service, planning_service
from app.services.family_recommendations_service import get_family_recommendations
from app.services.life_event_service import EntityEffect
from app.services.loan_payoff_handler import LoanPayoffHandler


async def _make_liability(
    db: AsyncSession,
    user: User,
    *,
    balance: float = 12_000.0,
    interest_rate: float | None = 0.22,
    monthly_payment: float = 400.0,
) -> Liability:
    liability = Liability(
        user_id=user.id,
        liability_type="credit_card",
        institution="Test Bank",
        description="Test card",
        balance=balance,
        interest_rate=interest_rate,
        monthly_payment=monthly_payment,
    )
    db.add(liability)
    await db.flush()
    return liability


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestLoanPayoffHandlerUnit:
    async def test_apply_closes_the_liability_and_returns_one_soft_delete_effect(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_liability(db, user)

        effects = await LoanPayoffHandler().apply(
            db, user, {"liability_id": str(liability.id)}
        )

        assert len(effects) == 1
        effect = effects[0]
        assert isinstance(effect, EntityEffect)
        assert effect.entity_table == "liabilities"
        assert effect.entity_id == liability.id
        assert effect.change_type == "soft_delete"
        assert effect.before_state["is_active"] is True
        assert effect.after_state["is_active"] is False
        # Balance/rate/payment are unchanged by a payoff — only is_active
        # flips — but both are captured so undo's conflict check would
        # notice if either drifted independently later.
        assert effect.before_state["balance"] == effect.after_state["balance"] == 12_000.0

        await db.refresh(liability)
        assert liability.is_active is False

    async def test_apply_raises_for_a_nonexistent_liability(
        self, db: AsyncSession, user: User
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await LoanPayoffHandler().apply(db, user, {"liability_id": str(uuid.uuid4())})
        assert exc_info.value.status_code == 404

    async def test_apply_raises_for_another_users_liability(
        self, db: AsyncSession, user: User, other_user: User
    ):
        from fastapi import HTTPException

        someone_elses_liability = await _make_liability(db, other_user)

        with pytest.raises(HTTPException) as exc_info:
            await LoanPayoffHandler().apply(
                db, user, {"liability_id": str(someone_elses_liability.id)}
            )
        assert exc_info.value.status_code == 404

        # Untouched — the 404 must fire before any write, not after.
        await db.refresh(someone_elses_liability)
        assert someone_elses_liability.is_active is True


# ── Integration: the full workflow through the generic engine ──────────────


class TestLoanPayoffFullWorkflow:
    async def test_records_life_event_and_effect_and_closes_the_liability(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_liability(db, user, balance=8_500.0)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date(2026, 3, 1),
            inputs={"liability_id": str(liability.id)},
        )

        assert life_event.event_type == "loan_payoff"
        assert life_event.status == "applied"
        assert life_event.occurred_on == date(2026, 3, 1)
        assert len(life_event.effects) == 1
        assert life_event.effects[0].entity_table == "liabilities"
        assert life_event.effects[0].entity_id == liability.id

        await db.refresh(liability)
        assert liability.is_active is False

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        liability = await _make_liability(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
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
            "event_type": "loan_payoff",
        }

    async def test_liability_still_appears_in_history_but_not_in_active_listing(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_liability(db, user)
        await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
        )

        result = await db.execute(
            select(Liability).where(
                Liability.user_id == user.id, Liability.is_active.is_(True)
            )
        )
        assert result.scalars().all() == []  # gone from the active list

        still_exists = await db.get(Liability, liability.id)
        assert still_exists is not None  # never hard-deleted


# ── Rollback: a failure after the write must leave nothing durable ─────────


class _LoanPayoffThenFailHandler:
    """Wraps the real handler so the real close_liability write actually
    happens (and gets flushed), then fails — proving record_life_event's
    "never commit" discipline (TransactionConsistencyImplementationPlan.md)
    means a caller's rollback discards the already-flushed liability
    change too, not just the LifeEvent/LifeEventEffect rows."""

    def __init__(self) -> None:
        self._real = LoanPayoffHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the liability was closed")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_liability(db, user, balance=15_000.0)
        liability_id = liability.id
        user_id = user.id
        # Commits the liability's *creation* as an established checkpoint —
        # exactly as it would already be durable from an earlier, separate
        # request in real use. Only the loan-payoff attempt below (a
        # second, failing "request") is what this test proves rolls back
        # cleanly; rolling back the liability's own pre-existing creation
        # too would prove nothing about this handler.
        await db.commit()
        life_event_service.register_handler("loan_payoff_then_fail", _LoanPayoffThenFailHandler())
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="loan_payoff_then_fail",
                    occurred_on=date.today(),
                    inputs={"liability_id": str(liability_id)},
                )

            await db.rollback()
            # session.rollback() expires every already-loaded object's
            # attributes (regardless of expire_on_commit) — `liability_id`/
            # `user_id` were captured as plain UUIDs above specifically so
            # nothing below touches an expired ORM attribute outside an
            # awaited context.

            # The liability's is_active=False (already flushed inside the
            # handler before the simulated failure) must not survive.
            reloaded = await db.get(Liability, liability_id)
            assert reloaded is not None
            assert reloaded.is_active is True
            assert reloaded.balance == 15_000.0

            # No LifeEvent/AuditLog row either — record_life_event never
            # got far enough to create them, and nothing it did before
            # failing was committed.
            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(
                select(AuditLog).where(
                    AuditLog.user_id == user_id, AuditLog.action == "life_event_recorded"
                )
            )
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("loan_payoff_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reactivates_the_liability_unchanged(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_liability(
            db, user, balance=9_000.0, interest_rate=0.18, monthly_payment=350.0
        )
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
        )

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        assert result.conflicts == []

        await db.refresh(liability)
        assert liability.is_active is True
        assert liability.balance == 9_000.0
        assert liability.interest_rate == 0.18
        assert liability.monthly_payment == 350.0

        await db.refresh(life_event)
        assert life_event.status == "undone"
        assert life_event.undone_at is not None

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_liability(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
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
        liability = await _make_liability(db, user, balance=5_000.0)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
        )

        # Simulate something independently touching the closed liability's
        # balance after the payoff was recorded.
        liability.balance = 999.0
        db.add(liability)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert len(result.conflicts) == 1
        assert result.conflicts[0].entity_table == "liabilities"

        unchanged = await db.get(Liability, liability.id)
        assert unchanged is not None
        assert unchanged.balance == 999.0
        assert unchanged.is_active is False  # undo did not proceed

    async def test_cannot_undo_another_users_loan_payoff(
        self, db: AsyncSession, user: User, other_user: User
    ):
        liability = await _make_liability(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_liabilities_total_drops_after_payoff(
        self, db: AsyncSession, user: User
    ):
        liability = await _make_liability(db, user, balance=20_000.0)

        before = await planning_service.get_dashboard(db, user)
        assert before.liabilities == 20_000.0

        await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
        )

        after = await planning_service.get_dashboard(db, user)
        assert after.liabilities == 0.0
        assert after.net_worth == before.net_worth + 20_000.0

    async def test_high_interest_debt_recommendation_stops_firing_after_payoff(
        self, db: AsyncSession, user: User
    ):
        # 22% is above family_recommendations_service's own
        # _HIGH_INTEREST_THRESHOLD (0.10) — reused, not restated, by this
        # test: it asserts on the live recommendation engine's actual
        # output, not a hardcoded expectation of what that threshold is.
        liability = await _make_liability(db, user, balance=6_000.0, interest_rate=0.22)
        household, _created = await family_service.get_or_create_household(db, user)

        # recommendation_type is suffixed per-liability
        # (f"high_interest_debt:{liability.id}", for uniqueness when more
        # than one qualifying liability exists) — reference_code is the
        # stable identifier for "this rule fired at all".
        before_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert any(r.reference_code == "high_interest_debt" for r in before_recs)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
        )

        after_recs, _conflicts = await get_family_recommendations(db, user, household)
        assert not any(r.reference_code == "high_interest_debt" for r in after_recs)
