"""Life Event Engine — Divorce (LifeEventEngineArchitecture.md §5.4).

Covers the handler in isolation, the full record/undo workflow through
the generic engine, a rollback proof, and the two new purely-live
"review" notification prompts this event added (insurance coverage,
nominee designations).
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.estate import Nominee
from app.models.financials import Asset
from app.models.household import Dependent, HouseholdMember
from app.models.insurance import HealthPolicy, HealthPolicyCoverage
from app.models.life_event import LifeEvent
from app.models.user import User
from app.services import family_service, life_event_service
from app.services.divorce_handler import DivorceHandler
from app.services.life_event_service import EntityEffect


async def _make_spouse(db: AsyncSession, user: User) -> tuple[HouseholdMember, Dependent]:
    household, _created = await family_service.get_or_create_household(db, user)
    member = HouseholdMember(household_id=household.id, relationship_type="spouse", name="Jamie")
    db.add(member)
    await db.flush()
    dependent = Dependent(
        household_member_id=member.id, dependent_type="spouse", date_of_birth=date(1990, 1, 1)
    )
    db.add(dependent)
    await db.flush()
    return member, dependent


# ── Unit tests: the handler in isolation ────────────────────────────────────


class TestDivorceHandlerUnit:
    async def test_apply_soft_deletes_member_and_dependent(
        self, db: AsyncSession, user: User
    ):
        member, dependent = await _make_spouse(db, user)

        effects = await DivorceHandler().apply(db, user, {"member_id": str(member.id)})

        assert len(effects) == 2
        member_effect, dependent_effect = effects
        assert isinstance(member_effect, EntityEffect)
        assert member_effect.entity_table == "household_members"
        assert member_effect.change_type == "soft_delete"
        assert member_effect.before_state["is_active"] is True
        assert member_effect.after_state["is_active"] is False

        assert dependent_effect.entity_table == "dependents"
        assert dependent_effect.change_type == "soft_delete"
        assert dependent_effect.after_state["is_active"] is False

        await db.refresh(member)
        await db.refresh(dependent)
        assert member.is_active is False
        assert dependent.is_active is False

    async def test_apply_raises_404_for_a_nonexistent_member(
        self, db: AsyncSession, user: User
    ):
        from uuid import uuid4

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await DivorceHandler().apply(db, user, {"member_id": str(uuid4())})
        assert exc_info.value.status_code == 404

    async def test_apply_raises_400_for_the_self_member(self, db: AsyncSession, user: User):
        from fastapi import HTTPException

        household, _created = await family_service.get_or_create_household(db, user)
        result = await db.execute(
            select(HouseholdMember).where(
                HouseholdMember.household_id == household.id,
                HouseholdMember.relationship_type == "self",
            )
        )
        self_member = result.scalar_one()

        with pytest.raises(HTTPException) as exc_info:
            await DivorceHandler().apply(db, user, {"member_id": str(self_member.id)})
        assert exc_info.value.status_code == 400


# ── Integration: the full workflow through the generic engine ──────────────


class TestDivorceFullWorkflow:
    async def test_records_life_event_and_both_effects(self, db: AsyncSession, user: User):
        member, _dependent = await _make_spouse(db, user)

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date(2026, 6, 1),
            inputs={"member_id": str(member.id)},
        )

        assert life_event.event_type == "divorce"
        assert life_event.status == "applied"
        assert len(life_event.effects) == 2

    async def test_writes_the_generic_audit_log_entry(self, db: AsyncSession, user: User):
        member, _dependent = await _make_spouse(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date.today(),
            inputs={"member_id": str(member.id)},
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
            "event_type": "divorce",
        }


# ── Rollback: a failure after the writes must leave nothing durable ────────


class _DivorceThenFailHandler:
    def __init__(self) -> None:
        self._real = DivorceHandler()

    async def apply(self, db, user, inputs):
        await self._real.apply(db, user, inputs)
        raise RuntimeError("simulated failure after the member/dependent writes")


class TestRollback:
    async def test_partial_failure_leaves_no_durable_change(
        self, db: AsyncSession, user: User
    ):
        member, dependent = await _make_spouse(db, user)
        member_id = member.id
        dependent_id = dependent.id
        user_id = user.id
        await db.commit()

        life_event_service.register_handler("divorce_then_fail", _DivorceThenFailHandler())
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await life_event_service.record_life_event(
                    db,
                    user,
                    event_type="divorce_then_fail",
                    occurred_on=date.today(),
                    inputs={"member_id": str(member_id)},
                )

            await db.rollback()

            reloaded_member = await db.get(HouseholdMember, member_id)
            reloaded_dependent = await db.get(Dependent, dependent_id)
            assert reloaded_member is not None and reloaded_member.is_active is True
            assert reloaded_dependent is not None and reloaded_dependent.is_active is True

            result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user_id))
            assert result.scalars().all() == []
        finally:
            life_event_service.unregister_handler("divorce_then_fail")


# ── Undo ────────────────────────────────────────────────────────────────────


class TestUndo:
    async def test_undo_reactivates_member_and_dependent(self, db: AsyncSession, user: User):
        member, dependent = await _make_spouse(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date.today(),
            inputs={"member_id": str(member.id)},
        )

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is False
        await db.refresh(member)
        await db.refresh(dependent)
        assert member.is_active is True
        assert dependent.is_active is True

    async def test_undo_writes_the_generic_audit_log_entry(
        self, db: AsyncSession, user: User
    ):
        member, _dependent = await _make_spouse(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date.today(),
            inputs={"member_id": str(member.id)},
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

    async def test_undo_blocked_if_the_member_changed_since_the_event(
        self, db: AsyncSession, user: User
    ):
        member, _dependent = await _make_spouse(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date.today(),
            inputs={"member_id": str(member.id)},
        )

        member.name = "Changed Name"
        db.add(member)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert any(c.entity_table == "household_members" for c in result.conflicts)

    async def test_cannot_undo_another_users_divorce(
        self, db: AsyncSession, user: User, other_user: User
    ):
        member, _dependent = await _make_spouse(db, user)
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date.today(),
            inputs={"member_id": str(member.id)},
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── New live "review" notification prompts ──────────────────────────────────


class TestDivorceReviewNotifications:
    async def test_life_event_notification_fires_for_divorce(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        member, _dependent = await _make_spouse(db, user)
        await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date.today(),
            inputs={"member_id": str(member.id)},
        )
        await db.commit()

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        life_event_items = [i for i in items if i["source"] == "life_event"]
        assert len(life_event_items) == 1
        assert life_event_items[0]["title"] == "Divorce recorded"

    async def test_no_review_prompts_before_any_divorce(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        assert [i for i in items if i["source"] == "divorce_review"] == []

    async def test_insurance_review_prompt_fires_for_a_still_covered_ex_spouse(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        member, _dependent = await _make_spouse(db, user)
        policy = HealthPolicy(
            primary_holder_user_id=user.id,
            policy_type="family_floater",
            sum_insured=1_000_000.0,
            annual_premium=20_000.0,
        )
        db.add(policy)
        await db.flush()
        coverage = HealthPolicyCoverage(health_policy_id=policy.id, household_member_id=member.id)
        db.add(coverage)
        await db.flush()

        await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date.today(),
            inputs={"member_id": str(member.id)},
        )
        await db.commit()

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        review_items = [i for i in items if i["source"] == "divorce_review"]
        assert any("Jamie" in i["title"] for i in review_items)

    async def test_nominee_review_prompt_fires_for_a_spouse_designated_nominee(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        member, _dependent = await _make_spouse(db, user)
        asset = Asset(user_id=user.id, asset_type="brokerage", current_value=100_000.0)
        db.add(asset)
        await db.flush()
        nominee = Nominee(
            asset_id=asset.id, name="Jamie", relationship_type="spouse", percentage_share=100.0
        )
        db.add(nominee)
        await db.flush()

        await life_event_service.record_life_event(
            db,
            user,
            event_type="divorce",
            occurred_on=date.today(),
            inputs={"member_id": str(member.id)},
        )
        await db.commit()

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        review_items = [i for i in items if i["source"] == "divorce_review"]
        assert any("beneficiary" in i["title"].lower() for i in review_items)

    async def test_nominee_review_prompt_does_not_fire_without_an_inactive_spouse(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        """A currently-married user with a spouse-designated nominee is
        never nagged — the review prompt is scoped to an inactive spouse
        actually existing, not just any active spouse-relationship
        Nominee row (see notification_service._collect_divorce_review_facts's
        own docstring for the reasoning)."""
        asset = Asset(user_id=user.id, asset_type="brokerage", current_value=50_000.0)
        db.add(asset)
        await db.flush()
        nominee = Nominee(
            asset_id=asset.id, name="Spouse", relationship_type="spouse", percentage_share=100.0
        )
        db.add(nominee)
        await db.commit()

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        assert [i for i in items if i["source"] == "divorce_review"] == []
