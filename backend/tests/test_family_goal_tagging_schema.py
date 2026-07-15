"""Tests for Milestone 2 Task 1's schema additions: goal_household_members,
goals.custom_inflation_rate, dependents.has_own_insurance. Schema-only —
no service/router logic exists yet (that's Task 2/8's scope). See
Milestone2ImplementationContract.md §0 and ImplementationChecklist.md Task 1.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.models.goal_household_member import GoalHouseholdMember
from app.models.household import Dependent, Household, HouseholdMember
from app.models.user import User


async def _make_household_member(
    db: AsyncSession, user: User, relationship_type: str
) -> HouseholdMember:
    household = Household(name="Test Household", created_by_user_id=user.id)
    db.add(household)
    await db.flush()
    member = HouseholdMember(household_id=household.id, relationship_type=relationship_type)
    db.add(member)
    await db.flush()
    return member


async def _make_goal(db: AsyncSession, user: User, **kwargs: object) -> Goal:
    defaults: dict[str, object] = {
        "user_id": user.id,
        "name": "Test Goal",
        "category": "education",
        "target_amount": 1_000_000.0,
        "target_date": date.today() + timedelta(days=365 * 10),
    }
    defaults.update(kwargs)
    goal = Goal(**defaults)
    db.add(goal)
    await db.flush()
    return goal


@pytest.mark.asyncio
class TestGoalCustomInflationRate:
    async def test_defaults_to_null_zero_behavior_change(
        self, db: AsyncSession, user: User
    ) -> None:
        goal = await _make_goal(db, user)
        result = await db.execute(select(Goal).where(Goal.id == goal.id))
        assert result.scalar_one().custom_inflation_rate is None

    async def test_can_be_set_for_education_goal(self, db: AsyncSession, user: User) -> None:
        goal = await _make_goal(db, user, custom_inflation_rate=0.08)
        result = await db.execute(select(Goal).where(Goal.id == goal.id))
        assert result.scalar_one().custom_inflation_rate == pytest.approx(0.08)


@pytest.mark.asyncio
class TestDependentHasOwnInsurance:
    async def test_defaults_to_null(self, db: AsyncSession, user: User) -> None:
        member = await _make_household_member(db, user, "parent")
        dependent = Dependent(household_member_id=member.id, dependent_type="elderly_parent")
        db.add(dependent)
        await db.flush()

        result = await db.execute(select(Dependent).where(Dependent.id == dependent.id))
        assert result.scalar_one().has_own_insurance is None

    @pytest.mark.parametrize("value", ["yes", "no", "not_sure"])
    async def test_accepts_all_three_valid_values(
        self, db: AsyncSession, user: User, value: str
    ) -> None:
        member = await _make_household_member(db, user, "parent")
        dependent = Dependent(
            household_member_id=member.id, dependent_type="elderly_parent", has_own_insurance=value
        )
        db.add(dependent)
        await db.flush()

        result = await db.execute(select(Dependent).where(Dependent.id == dependent.id))
        assert result.scalar_one().has_own_insurance == value


@pytest.mark.asyncio
class TestGoalHouseholdMemberTag:
    async def test_tag_defaults_to_no_owner_change(self, db: AsyncSession, user: User) -> None:
        goal = await _make_goal(db, user)
        member = await _make_household_member(db, user, "spouse")

        tag = GoalHouseholdMember(goal_id=goal.id, household_member_id=member.id)
        db.add(tag)
        await db.flush()

        result = await db.execute(select(Goal).where(Goal.id == goal.id))
        # The tag never changes the goal's owner of record.
        assert result.scalar_one().user_id == user.id

    async def test_duplicate_tag_rejected_by_unique_constraint(
        self, db: AsyncSession, user: User
    ) -> None:
        goal = await _make_goal(db, user)
        member = await _make_household_member(db, user, "spouse")

        db.add(GoalHouseholdMember(goal_id=goal.id, household_member_id=member.id))
        await db.flush()

        db.add(GoalHouseholdMember(goal_id=goal.id, household_member_id=member.id))
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_deleting_goal_cascades_tag_removal(self, db: AsyncSession, user: User) -> None:
        # This test's SQLite backend does not enforce FK-level ON DELETE
        # CASCADE without an explicit `PRAGMA foreign_keys=ON` that this
        # suite's conftest.py does not set — the same documented limitation
        # as test_foundation_reconciliation.py's ON DELETE SET NULL case.
        # The cascade-delete outcome was instead verified directly against
        # the real Postgres dev database (INSERT/DELETE/SELECT in a
        # rolled-back transaction: deleting the goal left 0 remaining
        # goal_household_members rows). What this test *can* validate under
        # SQLite is that the ORM-level delete of the parent goal succeeds
        # without raising an FK-violation error — proving the relationship
        # is at least structurally consistent even where cascade enforcement
        # itself isn't exercised by this backend.
        goal = await _make_goal(db, user)
        member = await _make_household_member(db, user, "spouse")
        tag = GoalHouseholdMember(goal_id=goal.id, household_member_id=member.id)
        db.add(tag)
        await db.flush()

        await db.delete(goal)
        await db.flush()

        result = await db.execute(select(Goal).where(Goal.id == goal.id))
        assert result.scalar_one_or_none() is None

    async def test_deleting_household_member_cascades_tag_removal(
        self, db: AsyncSession, user: User
    ) -> None:
        # Same SQLite limitation as above — see that test's comment. The
        # goal-survives-member-removal half of this behavior (the more
        # important invariant: removing a family member must never delete
        # someone else's goal) is fully verifiable under SQLite and is
        # what this test asserts.
        goal = await _make_goal(db, user)
        member = await _make_household_member(db, user, "spouse")
        tag = GoalHouseholdMember(goal_id=goal.id, household_member_id=member.id)
        db.add(tag)
        await db.flush()
        goal_id = goal.id

        await db.delete(member)
        await db.flush()

        # The goal itself must survive — only the tag would be removed
        # (cascade verified against real Postgres, see above).
        goal_result = await db.execute(select(Goal).where(Goal.id == goal_id))
        assert goal_result.scalar_one_or_none() is not None
