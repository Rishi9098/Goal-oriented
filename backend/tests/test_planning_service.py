"""Unit tests for pure (sync) planning service helpers."""

import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.planning_service as planning_service_module
from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.goal import Goal
from app.models.user import User
from app.schemas.simulation import DashboardSuggestion
from app.services.planning_service import (
    _active_goals,
    _generate_suggestions,
    calculate_goal_probability,
    compute_plan_health,
    get_dashboard,
    get_financial_context,
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
class TestCalculateGoalProbability:
    """ADR-001: calculate_goal_probability is the sole, centralized Monte
    Carlo trigger — called only from goal create/update, never from a read."""

    async def _make_goal(self, db: AsyncSession, **kwargs: object) -> Goal:
        user = User(email=f"calc-{uuid.uuid4()}@example.com", hashed_password="x")
        db.add(user)
        await db.flush()
        defaults: dict[str, object] = dict(
            user_id=user.id,
            name="Test Goal",
            category="wealth",
            target_amount=100_000,
            current_amount=1_000,
            target_date=date.today() + timedelta(days=365 * 5),
            monthly_contribution=200,
            risk_profile="balanced",
        )
        defaults.update(kwargs)
        goal = Goal(**defaults)
        db.add(goal)
        await db.flush()
        return goal

    async def test_sets_probability_and_on_track_from_simulation_result(
        self, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_quick_probability_async(**_kwargs: object) -> float:
            return 82.345

        monkeypatch.setattr(
            planning_service_module, "quick_probability_async", fake_quick_probability_async
        )

        goal = await self._make_goal(db)
        await calculate_goal_probability(goal)

        assert goal.probability == 82.3
        assert goal.on_track is True

    async def test_below_threshold_is_not_on_track(
        self, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_quick_probability_async(**_kwargs: object) -> float:
            return 45.0

        monkeypatch.setattr(
            planning_service_module, "quick_probability_async", fake_quick_probability_async
        )

        goal = await self._make_goal(db)
        await calculate_goal_probability(goal)

        assert goal.on_track is False

    async def test_forwards_configured_seed_for_reproducibility(
        self, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mirrors how routers/simulate.py already seeds the full engine —
        the centralized trigger must not be a parallel, unseeded path."""
        captured: dict[str, object] = {}

        async def fake_quick_probability_async(**kwargs: object) -> float:
            captured.update(kwargs)
            return 75.0

        monkeypatch.setattr(
            planning_service_module, "quick_probability_async", fake_quick_probability_async
        )
        monkeypatch.setattr(planning_service_module.settings, "monte_carlo_seed", 42)

        goal = await self._make_goal(db)
        await calculate_goal_probability(goal)

        assert captured["seed"] == 42

    async def test_active_goals_excludes_inactive_and_other_users(
        self, db: AsyncSession
    ) -> None:
        goal = await self._make_goal(db)
        other_user_goal = await self._make_goal(db)
        inactive_goal = await self._make_goal(db, user_id=goal.user_id, is_active=False)

        result = await _active_goals(db, goal.user_id)

        result_ids = {g.id for g in result}
        assert goal.id in result_ids
        assert other_user_goal.id not in result_ids
        assert inactive_goal.id not in result_ids


@pytest.mark.asyncio
class TestGetFinancialContext:
    """Recommendation Engine v2, Phase A (RecommendationEngineV2.md §3,
    RecommendationEngineV2Validation.md item 1): FinancialContext must be
    the single source of truth get_dashboard() itself now consumes.
    Every test here asserts both (a) FinancialContext's own values are
    arithmetically correct, and (b) get_dashboard()'s response is exactly
    derivable from that same FinancialContext — proving there is no second,
    diverging implementation of this math anywhere."""

    async def _make_user(self, db: AsyncSession) -> User:
        user = User(email=f"fc-{uuid.uuid4()}@example.com", hashed_password="x")
        db.add(user)
        await db.flush()
        return user

    async def _make_goal(self, db: AsyncSession, user: User, **kwargs: object) -> Goal:
        defaults: dict[str, object] = dict(
            user_id=user.id,
            name="Retirement",
            category="retirement",
            target_amount=500_000,
            current_amount=20_000,
            target_date=date.today() + timedelta(days=365 * 20),
            monthly_contribution=500,
            risk_profile="balanced",
            probability=13.9,
            on_track=False,
        )
        defaults.update(kwargs)
        goal = Goal(**defaults)
        db.add(goal)
        await db.flush()
        return goal

    async def test_normal_account_matches_manual_arithmetic_and_dashboard(
        self, db: AsyncSession
    ) -> None:
        """Income + expenses + assets + liabilities all present — the
        'normal' branch, no fallback."""
        user = await self._make_user(db)
        db.add(IncomeSource(user_id=user.id, source_type="salary", annual_amount=156_000))
        db.add(Expense(user_id=user.id, category="housing", monthly_amount=2_800))
        db.add(Asset(user_id=user.id, asset_type="savings", current_value=35_000))
        db.add(
            Liability(
                user_id=user.id,
                liability_type="mortgage",
                balance=280_000,
                interest_rate=0.06,
                monthly_payment=1_800,
            )
        )
        goal = await self._make_goal(db, user)
        await db.commit()

        active_goals = [goal]
        context = await get_financial_context(db, user, active_goals)

        assert context.monthly_income == pytest.approx(156_000 / 12)
        assert context.monthly_expenses == pytest.approx(2_800)
        assert context.monthly_savings == pytest.approx(156_000 / 12 - 2_800)
        assert context.savings_rate == pytest.approx((13_000 - 2_800) / 13_000 * 100)
        assert context.total_assets == pytest.approx(35_000)
        assert context.liquid_assets == pytest.approx(35_000)
        assert context.invested_assets == pytest.approx(0.0)
        assert context.total_liabilities == pytest.approx(280_000)
        assert context.net_worth == pytest.approx(35_000 - 280_000)
        assert context.debt_ratio == pytest.approx(280_000 / 156_000)

        dashboard = await get_dashboard(db, user)
        assert dashboard.net_worth == pytest.approx(context.net_worth)
        assert dashboard.liquid_assets == pytest.approx(context.liquid_assets)
        assert dashboard.invested == pytest.approx(context.invested_assets)
        assert dashboard.liabilities == pytest.approx(context.total_liabilities)
        assert dashboard.monthly_income == round(context.monthly_income, 2)
        assert dashboard.monthly_expenses == round(context.monthly_expenses, 2)
        assert dashboard.monthly_savings_rate == round(context.savings_rate, 1)

    async def test_zero_asset_liability_account_falls_back_to_goal_totals(
        self, db: AsyncSession
    ) -> None:
        """RecommendationEngineV2Validation.md's required correction: no
        Asset/Liability rows, but real income/expense rows and a goal —
        net_worth/invested must fall back to goal current_amount totals,
        while monthly_income/expenses/savings_rate stay real, and
        total_assets/total_liabilities/liquid_assets stay honestly 0."""
        user = await self._make_user(db)
        db.add(IncomeSource(user_id=user.id, source_type="salary", annual_amount=120_000))
        db.add(Expense(user_id=user.id, category="housing", monthly_amount=2_000))
        goal = await self._make_goal(db, user, current_amount=20_000)
        await db.commit()

        active_goals = [goal]
        context = await get_financial_context(db, user, active_goals)

        assert context.net_worth == pytest.approx(20_000)
        assert context.invested_assets == pytest.approx(20_000)
        assert context.liquid_assets == 0.0
        assert context.total_assets == 0.0
        assert context.total_liabilities == 0.0
        assert context.debt_ratio == 0.0
        assert context.monthly_income == pytest.approx(10_000)
        assert context.monthly_expenses == pytest.approx(2_000)
        assert context.savings_rate == pytest.approx(80.0)

        dashboard = await get_dashboard(db, user)
        assert dashboard.net_worth == pytest.approx(context.net_worth)
        assert dashboard.invested == pytest.approx(context.invested_assets)
        assert dashboard.liquid_assets == 0.0
        assert dashboard.liabilities == 0.0
        assert dashboard.monthly_income == round(context.monthly_income, 2)
        assert dashboard.monthly_expenses == round(context.monthly_expenses, 2)
        assert dashboard.monthly_savings_rate == round(context.savings_rate, 1)

    async def test_goal_only_account_has_no_financial_facts_at_all(
        self, db: AsyncSession
    ) -> None:
        """No income, expense, asset, or liability rows — only a goal.
        Every ratio guarded against division by zero must resolve to 0.0,
        not raise, and the fallback must still apply."""
        user = await self._make_user(db)
        goal = await self._make_goal(db, user, current_amount=5_000)
        await db.commit()

        active_goals = [goal]
        context = await get_financial_context(db, user, active_goals)

        assert context.monthly_income == 0.0
        assert context.monthly_expenses == 0.0
        assert context.monthly_savings == 0.0
        assert context.savings_rate == 0.0
        assert context.debt_ratio == 0.0
        assert context.net_worth == pytest.approx(5_000)
        assert context.invested_assets == pytest.approx(5_000)
        assert context.liquid_assets == 0.0
        assert context.total_assets == 0.0
        assert context.total_liabilities == 0.0

        dashboard = await get_dashboard(db, user)
        assert dashboard.net_worth == pytest.approx(context.net_worth)
        assert dashboard.monthly_income == 0.0
        assert dashboard.monthly_expenses == 0.0
        assert dashboard.monthly_savings_rate == 0.0

    async def test_mixed_account_assets_and_liabilities_but_no_income(
        self, db: AsyncSession
    ) -> None:
        """Assets/liabilities present (so the 'normal' branch runs, not the
        fallback), but zero income rows — the savings_rate and debt_ratio
        guards must both resolve to 0.0 in the non-fallback branch too,
        distinct from the zero-asset-and-liability fallback case above."""
        user = await self._make_user(db)
        db.add(Asset(user_id=user.id, asset_type="checking", current_value=10_000))
        db.add(
            Liability(
                user_id=user.id, liability_type="car_loan", balance=8_000, monthly_payment=300
            )
        )
        goal = await self._make_goal(db, user, current_amount=1_000)
        await db.commit()

        active_goals = [goal]
        context = await get_financial_context(db, user, active_goals)

        assert context.monthly_income == 0.0
        assert context.monthly_expenses == 0.0
        assert context.savings_rate == 0.0
        assert context.debt_ratio == 0.0
        assert context.total_assets == pytest.approx(10_000)
        assert context.liquid_assets == pytest.approx(10_000)
        assert context.total_liabilities == pytest.approx(8_000)
        # Normal branch, not the fallback: net_worth is real assets minus
        # real liabilities, NOT the goal current_amount total (1_000).
        assert context.net_worth == pytest.approx(10_000 - 8_000)

        dashboard = await get_dashboard(db, user)
        assert dashboard.net_worth == pytest.approx(context.net_worth)
        assert dashboard.liquid_assets == pytest.approx(context.liquid_assets)
        assert dashboard.liabilities == pytest.approx(context.total_liabilities)
        assert dashboard.monthly_savings_rate == 0.0

    async def test_liabilities_field_carries_raw_rows_not_just_the_sum(
        self, db: AsyncSession
    ) -> None:
        """Phase B (RecommendationEngineV2Validation.md item 7): a future
        high_interest_debt rule needs each liability's own interest_rate,
        not just their combined balance — confirm the raw rows are present
        and individually inspectable, and that this addition does not
        change total_liabilities or net_worth."""
        user = await self._make_user(db)
        db.add(
            Liability(
                user_id=user.id,
                liability_type="mortgage",
                balance=280_000,
                interest_rate=0.06,
                monthly_payment=1_800,
            )
        )
        db.add(
            Liability(
                user_id=user.id,
                liability_type="credit_card",
                balance=5_000,
                interest_rate=0.22,
                monthly_payment=200,
            )
        )
        db.add(Asset(user_id=user.id, asset_type="checking", current_value=10_000))
        goal = await self._make_goal(db, user, current_amount=1_000)
        await db.commit()

        context = await get_financial_context(db, user, [goal])

        assert len(context.liabilities) == 2
        rates_by_type = {lb.liability_type: lb.interest_rate for lb in context.liabilities}
        assert rates_by_type["mortgage"] == pytest.approx(0.06)
        assert rates_by_type["credit_card"] == pytest.approx(0.22)
        # Unchanged by this addition:
        assert context.total_liabilities == pytest.approx(285_000)
        assert context.net_worth == pytest.approx(10_000 - 285_000)

    async def test_expenses_last_updated_at_reflects_most_recent_edit(
        self, db: AsyncSession
    ) -> None:
        """Phase B: a future expense_review_prompt rule needs a staleness
        signal the aggregate fields can't provide."""
        user = await self._make_user(db)
        db.add(Expense(user_id=user.id, category="housing", monthly_amount=2_000))
        db.add(Expense(user_id=user.id, category="food", monthly_amount=500))
        goal = await self._make_goal(db, user, current_amount=1_000)
        await db.commit()

        context = await get_financial_context(db, user, [goal])

        assert context.expenses_last_updated_at is not None
        # Unchanged by this addition:
        assert context.monthly_expenses == pytest.approx(2_500)

    async def test_expenses_last_updated_at_is_none_with_no_expenses(
        self, db: AsyncSession
    ) -> None:
        """No expense rows at all — there is no edit to be stale, so the
        field must be None, not a fabricated timestamp."""
        user = await self._make_user(db)
        goal = await self._make_goal(db, user, current_amount=1_000)
        await db.commit()

        context = await get_financial_context(db, user, [goal])

        assert context.expenses_last_updated_at is None
        assert context.liabilities == []
