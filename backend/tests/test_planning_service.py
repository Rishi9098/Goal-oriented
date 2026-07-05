"""Unit tests for pure (sync) planning service helpers."""

import asyncio
import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.planning_service as planning_service_module
from app.models.goal import Goal
from app.models.user import User
from app.schemas.simulation import DashboardSuggestion
from app.services.planning_service import (
    _generate_suggestions,
    compute_plan_health,
    refresh_goal_probabilities,
)


def _make_goal(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Goal",
        category="education",
        target_amount=50_000,
        current_amount=10_000,
        target_date=date.today() + timedelta(days=365 * 5),
        monthly_contribution=500,
        risk_profile="balanced",
        probability=80.0,
        on_track=True,
        is_active=True,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestComputePlanHealth:
    def test_empty_goals_returns_zero(self):
        assert compute_plan_health([]) == 0

    def test_zero_total_weight_returns_zero(self):
        goal = _make_goal(target_amount=0)
        assert compute_plan_health([goal]) == 0

    def test_single_goal_probability(self):
        goal = _make_goal(target_amount=100_000, probability=75.0)
        assert compute_plan_health([goal]) == 75

    def test_weighted_by_target_amount(self):
        g1 = _make_goal(target_amount=100_000, probability=60.0)
        g2 = _make_goal(target_amount=300_000, probability=100.0)
        result = compute_plan_health([g1, g2])
        # weighted: (60*100k + 100*300k) / 400k = (6M + 30M)/400k = 90
        assert result == 90

    def test_capped_at_100(self):
        goal = _make_goal(target_amount=50_000, probability=150.0)
        assert compute_plan_health([goal]) == 100

    def test_floored_at_0(self):
        goal = _make_goal(target_amount=50_000, probability=-10.0)
        assert compute_plan_health([goal]) == 0


class TestGenerateSuggestions:
    def test_no_retirement_goal_adds_suggestion(self):
        goal = _make_goal(category="education", probability=85.0)
        suggestions = _generate_suggestions([goal], savings_rate=20.0)
        ids = [s.id for s in suggestions]
        assert "no_retirement" in ids

    def test_retirement_goal_suppresses_suggestion(self):
        goal = _make_goal(category="retirement", probability=85.0)
        suggestions = _generate_suggestions([goal], savings_rate=20.0)
        ids = [s.id for s in suggestions]
        assert "no_retirement" not in ids

    def test_no_emergency_goal_adds_suggestion(self):
        goal = _make_goal(category="retirement", probability=85.0)
        suggestions = _generate_suggestions([goal], savings_rate=20.0)
        ids = [s.id for s in suggestions]
        assert "no_emergency" in ids

    def test_emergency_goal_suppresses_suggestion(self):
        g1 = _make_goal(category="retirement", probability=85.0)
        g2 = _make_goal(category="emergency", probability=85.0)
        suggestions = _generate_suggestions([g1, g2], savings_rate=20.0)
        ids = [s.id for s in suggestions]
        assert "no_emergency" not in ids

    def test_low_savings_rate_adds_suggestion(self):
        goal = _make_goal(category="retirement", probability=85.0)
        suggestions = _generate_suggestions([goal], savings_rate=5.0)
        ids = [s.id for s in suggestions]
        assert "low_savings_rate" in ids

    def test_zero_savings_rate_no_suggestion(self):
        goal = _make_goal(category="retirement", probability=85.0)
        suggestions = _generate_suggestions([goal], savings_rate=0.0)
        ids = [s.id for s in suggestions]
        assert "low_savings_rate" not in ids

    def test_critical_probability_warning(self):
        goal = _make_goal(name="My Goal", probability=30.0)
        suggestions = _generate_suggestions([goal], savings_rate=20.0)
        ids = [s.id for s in suggestions]
        assert f"prob_{goal.id}" in ids
        matched = next(s for s in suggestions if s.id == f"prob_{goal.id}")
        assert matched.severity == "warning"

    def test_moderate_probability_warning(self):
        goal = _make_goal(name="My Goal", probability=62.0)
        suggestions = _generate_suggestions([goal], savings_rate=20.0)
        ids = [s.id for s in suggestions]
        assert f"prob_{goal.id}" in ids

    def test_high_probability_no_prob_suggestion(self):
        goal = _make_goal(name="My Goal", probability=80.0)
        suggestions = _generate_suggestions([goal], savings_rate=20.0)
        ids = [s.id for s in suggestions]
        assert f"prob_{goal.id}" not in ids

    def test_suggestions_capped_at_five(self):
        goals = [_make_goal(probability=20.0, name=f"Goal {i}") for i in range(10)]
        suggestions = _generate_suggestions(goals, savings_rate=5.0)
        assert len(suggestions) <= 5

    def test_returns_list_of_dashboard_suggestions(self):
        goal = _make_goal(probability=85.0, category="retirement")
        result = _generate_suggestions([goal], savings_rate=0.0)
        assert all(isinstance(s, DashboardSuggestion) for s in result)


@pytest.mark.asyncio
class TestRefreshGoalProbabilitiesConcurrency:
    """AUDIT.md #9: simulations must dispatch concurrently, not sequentially."""

    async def _make_user_with_goals(self, db: AsyncSession, count: int) -> tuple[User, list[Goal]]:
        user = User(email=f"concurrency-{uuid.uuid4()}@example.com", hashed_password="x")
        db.add(user)
        await db.flush()

        goals = []
        for i in range(count):
            goal = Goal(
                user_id=user.id,
                name=f"Goal {i}",
                category="wealth",
                target_amount=100_000,
                current_amount=1_000,
                target_date=date.today() + timedelta(days=365 * 5),
                monthly_contribution=200,
                risk_profile="balanced",
            )
            db.add(goal)
            goals.append(goal)
        await db.flush()
        return user, goals

    async def test_dispatches_simulations_concurrently(
        self, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        in_flight = 0
        max_in_flight = 0
        lock = asyncio.Lock()

        async def fake_quick_probability_async(**_kwargs: object) -> float:
            nonlocal in_flight, max_in_flight
            async with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.05)
            async with lock:
                in_flight -= 1
            return 75.0

        monkeypatch.setattr(
            planning_service_module, "quick_probability_async", fake_quick_probability_async
        )

        user, goals = await self._make_user_with_goals(db, count=5)
        await refresh_goal_probabilities(db, user.id)

        # If dispatch were still sequential (one `await` per goal in a for
        # loop), max_in_flight could never exceed 1.
        assert max_in_flight > 1
        assert all(g.probability == 75.0 for g in goals)
        assert all(g.on_track for g in goals)

    async def test_results_map_back_to_the_correct_goal(
        self, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_quick_probability_async(*, target_amount: float, **_kwargs: object) -> float:
            # Distinct, deterministic per-goal result derived from an input
            # that's unique per goal, to catch any index/order mismatch bug.
            return target_amount / 1000

        monkeypatch.setattr(
            planning_service_module, "quick_probability_async", fake_quick_probability_async
        )

        user = User(email=f"mapping-{uuid.uuid4()}@example.com", hashed_password="x")
        db.add(user)
        await db.flush()

        goals = []
        for target in (10_000, 20_000, 30_000):
            goal = Goal(
                user_id=user.id,
                name=f"Goal {target}",
                category="wealth",
                target_amount=target,
                current_amount=0,
                target_date=date.today() + timedelta(days=365),
                monthly_contribution=100,
                risk_profile="balanced",
            )
            db.add(goal)
            goals.append(goal)
        await db.flush()

        await refresh_goal_probabilities(db, user.id)

        for goal in goals:
            assert goal.probability == goal.target_amount / 1000
