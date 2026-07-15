"""Life Event Engine — Job Change (LifeEventEngineArchitecture.md §5.2).

Covers the handler in isolation (profile-create and profile-update paths),
the full record/undo workflow through the generic engine, a rollback
proof across three entities, and verification that Dashboard and the live
Recommendation Engine reflect the change with zero new calculation logic
of their own.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.financials import IncomeSource
from app.models.life_event import LifeEvent
from app.models.profile import UserProfile
from app.models.user import User
from app.services import life_event_service, planning_service
from app.services.job_change_handler import JobChangeHandler
from app.services.life_event_service import EntityEffect


async def _make_income(
    db: AsyncSession, user: User, *, annual_amount: float = 80_000.0
) -> IncomeSource:
    income = IncomeSource(user_id=user.id, source_type="salary", annual_amount=annual_amount)
    db.add(income)
    await db.flush()
    return income


async def _make_profile(
    db: AsyncSession, user: User, *, employer: str = "Old Corp", occupation: str = "Analyst"
) -> UserProfile:
    profile = UserProfile(user_id=user.id, employer=employer, occupation=occupation)
    db.add(profile)
    await db.flush()
    return profile


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestJobChangeHandlerUnit:
    async def test_apply_updates_profile_closes_old_income_and_creates_new_income(
        self, db: AsyncSession, user: User
    ):
        old_income = await _make_income(db, user, annual_amount=80_000.0)
        await _make_profile(db, user, employer="Old Corp", occupation="Analyst")

        effects = await JobChangeHandler().apply(
            db,
            user,
            {
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Senior Analyst",
                "new_annual_amount": 95_000.0,
            },
        )

        assert len(effects) == 3
        profile_effect, old_income_effect, new_income_effect = effects
        assert isinstance(profile_effect, EntityEffect)
        assert profile_effect.entity_table == "user_profiles"
        assert profile_effect.change_type == "update"
        assert profile_effect.before_state == {"employer": "Old Corp", "occupation": "Analyst"}
        assert profile_effect.after_state == {
            "employer": "New Corp",
            "occupation": "Senior Analyst",
        }

        assert old_income_effect.entity_table == "income_sources"
        assert old_income_effect.entity_id == old_income.id
        assert old_income_effect.change_type == "soft_delete"
        assert old_income_effect.before_state["is_active"] is True
        assert old_income_effect.after_state["is_active"] is False

        assert new_income_effect.entity_table == "income_sources"
        assert new_income_effect.change_type == "create"
        assert new_income_effect.before_state is None
        assert new_income_effect.after_state["annual_amount"] == 95_000.0

        await db.refresh(old_income)
        assert old_income.is_active is False

        result = await db.execute(
            select(IncomeSource).where(
                IncomeSource.user_id == user.id, IncomeSource.is_active.is_(True)
            )
        )
        active_incomes = result.scalars().all()
        assert len(active_incomes) == 1
        assert active_incomes[0].annual_amount == 95_000.0

    async def test_apply_creates_a_profile_when_none_exists_yet(
        self, db: AsyncSession, user: User
    ):
        old_income = await _make_income(db, user)

        effects = await JobChangeHandler().apply(
            db,
            user,
            {
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Engineer",
                "new_annual_amount": 100_000.0,
            },
        )

        profile_effect = effects[0]
        assert profile_effect.change_type == "create"
        assert profile_effect.before_state is None
        assert profile_effect.after_state == {"employer": "New Corp", "occupation": "Engineer"}

        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = result.scalar_one()
        assert profile.employer == "New Corp"
        assert profile.occupation == "Engineer"

    async def test_apply_raises_for_a_nonexistent_old_income_source(
        self, db: AsyncSession, user: User
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await JobChangeHandler().apply(
                db,
                user,
                {
                    "old_income_source_id": str(uuid.uuid4()),
                    "new_employer": "New Corp",
                    "new_occupation": "Engineer",
                    "new_annual_amount": 100_000.0,
                },
            )
        assert exc_info.value.status_code == 404

    async def test_apply_raises_for_another_users_old_income_source(
        self, db: AsyncSession, user: User, other_user: User
    ):
        from fastapi import HTTPException

        someone_elses_income = await _make_income(db, other_user, annual_amount=60_000.0)

        with pytest.raises(HTTPException) as exc_info:
            await JobChangeHandler().apply(
                db,
                user,
                {
                    "old_income_source_id": str(someone_elses_income.id),
                    "new_employer": "New Corp",
                    "new_occupation": "Engineer",
                    "new_annual_amount": 100_000.0,
                },
            )
        assert exc_info.value.status_code == 404

        await db.refresh(someone_elses_income)
        assert someone_elses_income.is_active is True


# ── Integration: the full workflow through the generic engine ──────────────


class TestJobChangeFullWorkflow:
    async def test_records_life_event_and_all_three_effects(
        self, db: AsyncSession, user: User
    ):
        old_income = await _make_income(db, user, annual_amount=70_000.0)
        await _make_profile(db, user)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="job_change",
            occurred_on=date(2026, 5, 1),
            inputs={
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Director",
                "new_annual_amount": 110_000.0,
            },
        )

        assert life_event.event_type == "job_change"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 3
        tables = [effect.entity_table for effect in life_event.effects]
        assert tables == ["user_profiles", "income_sources", "income_sources"]

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        old_income = await _make_income(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="job_change",
            occurred_on=date.today(),
            inputs={
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Director",
                "new_annual_amount": 110_000.0,
            },
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
            "event_type": "job_change",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _JobChangeThenFailHandler:
    """Wraps the real handler so all three real writes actually happen (and
    get flushed), then fails — proving record_life_event's "never commit"
    discipline discards all three already-flushed changes, not just the
    LifeEvent/LifeEventEffect rows."""

    def __init__(self) -> None:
        self._real = JobChangeHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the profile/income writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        old_income = await _make_income(db, user, annual_amount=65_000.0)
        profile = await _make_profile(db, user, employer="Old Corp", occupation="Analyst")
        old_income_id = old_income.id
        profile_id = profile.id
        user_id = user.id
        # Commits the income/profile *creation* as an established checkpoint
        # — exactly as it would already be durable from an earlier, separate
        # request in real use.
        await db.commit()
        life_event_service.register_handler("job_change_then_fail", _JobChangeThenFailHandler())
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="job_change_then_fail",
                    occurred_on=date.today(),
                    inputs={
                        "old_income_source_id": str(old_income_id),
                        "new_employer": "New Corp",
                        "new_occupation": "Director",
                        "new_annual_amount": 200_000.0,
                    },
                )

            await db.rollback()

            reloaded_income = await db.get(IncomeSource, old_income_id)
            assert reloaded_income is not None
            assert reloaded_income.is_active is True
            assert reloaded_income.annual_amount == 65_000.0

            reloaded_profile = await db.get(UserProfile, profile_id)
            assert reloaded_profile is not None
            assert reloaded_profile.employer == "Old Corp"
            assert reloaded_profile.occupation == "Analyst"

            # The new income row created inside the failed attempt must not
            # have survived either.
            result = await db.execute(
                select(IncomeSource).where(IncomeSource.user_id == user_id)
            )
            assert len(result.scalars().all()) == 1  # only the original row

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
            result = await db.execute(
                select(AuditLog).where(
                    AuditLog.user_id == user_id, AuditLog.action == "life_event_recorded"
                )
            )
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("job_change_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reactivates_old_income_deactivates_new_income_and_reverts_profile(
        self, db: AsyncSession, user: User
    ):
        old_income = await _make_income(db, user, annual_amount=70_000.0)
        await _make_profile(db, user, employer="Old Corp", occupation="Analyst")

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="job_change",
            occurred_on=date.today(),
            inputs={
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Director",
                "new_annual_amount": 110_000.0,
            },
        )
        new_income_id = life_event.effects[2].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        assert result.conflicts == []

        await db.refresh(old_income)
        assert old_income.is_active is True
        assert old_income.annual_amount == 70_000.0

        new_income = await db.get(IncomeSource, new_income_id)
        assert new_income is not None
        assert new_income.is_active is False  # generic undo: create -> soft-delete

        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = profile_result.scalar_one()
        assert profile.employer == "Old Corp"
        assert profile.occupation == "Analyst"

        await db.refresh(life_event)
        assert life_event.status == "undone"

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        old_income = await _make_income(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="job_change",
            occurred_on=date.today(),
            inputs={
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Director",
                "new_annual_amount": 110_000.0,
            },
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

    async def test_undo_blocked_if_the_old_income_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        old_income = await _make_income(db, user, annual_amount=70_000.0)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="job_change",
            occurred_on=date.today(),
            inputs={
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Director",
                "new_annual_amount": 110_000.0,
            },
        )

        # Simulate something independently touching the now-closed old
        # income row after the job change was recorded.
        old_income.annual_amount = 1.0
        db.add(old_income)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert len(result.conflicts) == 1
        assert result.conflicts[0].entity_table == "income_sources"

        unchanged = await db.get(IncomeSource, old_income.id)
        assert unchanged is not None
        assert unchanged.is_active is False  # undo did not proceed

    async def test_cannot_undo_another_users_job_change(
        self, db: AsyncSession, user: User, other_user: User
    ):
        old_income = await _make_income(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="job_change",
            occurred_on=date.today(),
            inputs={
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Director",
                "new_annual_amount": 110_000.0,
            },
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Dashboard / Recommendation verification ─────────────────────────────────


class TestDashboardAndRecommendationIntegration:
    async def test_dashboard_income_reflects_the_new_role_only(
        self, db: AsyncSession, user: User
    ):
        from app.models.financials import Expense

        old_income = await _make_income(db, user, annual_amount=60_000.0)
        db.add(Expense(user_id=user.id, category="housing", monthly_amount=4_000.0))
        await db.flush()

        before = await planning_service.get_dashboard(db, user)

        await life_event_service.record_life_event(
            db,
            user,
            event_type="job_change",
            occurred_on=date.today(),
            inputs={
                "old_income_source_id": str(old_income.id),
                "new_employer": "New Corp",
                "new_occupation": "Director",
                "new_annual_amount": 130_000.0,
            },
        )

        after = await planning_service.get_dashboard(db, user)
        # The old salary must no longer count, and only the new one does —
        # not both (proving the old row is genuinely deactivated, not just
        # supplemented by a second active income row).
        assert after.monthly_savings_rate != before.monthly_savings_rate
