import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.goal import Goal
from app.models.user import User
from app.schemas.simulation import DashboardResponse, DashboardSuggestion
from app.services.monte_carlo import quick_probability_async

_LIQUID_ASSET_TYPES = frozenset({"checking", "savings", "money_market"})
_INVESTED_ASSET_TYPES = frozenset({"brokerage", "retirement_401k", "retirement_ira"})


async def refresh_goal_probabilities(
    session: AsyncSession, user_id: "uuid.UUID | str"
) -> list[Goal]:
    result = await session.execute(
        select(Goal).where(Goal.user_id == user_id, Goal.is_active.is_(True))
    )
    goals = list(result.scalars().all())

    today = date.today()
    for goal in goals:
        years = max(0.1, (goal.target_date - today).days / 365.25)
        prob = await quick_probability_async(
            initial_amount=goal.current_amount,
            monthly_contribution=goal.monthly_contribution,
            years_to_goal=years,
            risk_profile=goal.risk_profile,
            target_amount=goal.target_amount,
        )
        goal.probability = round(prob, 1)
        goal.on_track = prob >= 70.0
        session.add(goal)

    return goals


def compute_plan_health(goals: list[Goal]) -> int:
    if not goals:
        return 0

    total_weight = sum(g.target_amount for g in goals)
    if total_weight == 0:
        return 0

    weighted_sum = sum(g.probability * g.target_amount for g in goals)
    raw = weighted_sum / total_weight
    return min(100, max(0, round(raw)))


def _generate_suggestions(goals: list[Goal], savings_rate: float) -> list[DashboardSuggestion]:
    suggestions: list[DashboardSuggestion] = []

    for goal in goals:
        if goal.probability < 50:
            suggestions.append(DashboardSuggestion(
                id=f"prob_{goal.id}",
                title=f'Boost "{goal.name}" — only {goal.probability:.0f}% on track',
                impact="Increasing monthly contributions could raise success probability above 70%.",
                severity="warning",
            ))
        elif goal.probability < 70:
            suggestions.append(DashboardSuggestion(
                id=f"prob_{goal.id}",
                title=f'"{goal.name}" needs attention ({goal.probability:.0f}%)',
                impact="Consider increasing contributions or extending the timeline.",
                severity="warning",
            ))

    has_retirement = any(g.category == "retirement" for g in goals)
    if not has_retirement:
        suggestions.append(DashboardSuggestion(
            id="no_retirement",
            title="No retirement goal found",
            impact="Add a retirement goal so the simulator can project your long-term outlook.",
            severity="info",
        ))

    has_emergency = any(g.category == "emergency" for g in goals)
    if not has_emergency:
        suggestions.append(DashboardSuggestion(
            id="no_emergency",
            title="Consider an emergency fund goal",
            impact="3–6 months of expenses in a liquid account protects against unexpected events.",
            severity="info",
        ))

    if 0 < savings_rate < 15:
        suggestions.append(DashboardSuggestion(
            id="low_savings_rate",
            title=f"Savings rate is {savings_rate:.0f}% — below the 15% target",
            impact="Review your monthly expenses to find areas to reduce spending.",
            severity="info",
        ))

    return suggestions[:5]


async def get_dashboard(session: AsyncSession, user: User) -> DashboardResponse:
    goals = await refresh_goal_probabilities(session, user.id)

    active_goals = [g for g in goals if g.is_active]
    on_track_count = sum(1 for g in active_goals if g.on_track)
    health = compute_plan_health(active_goals)

    retirement_goals = [g for g in active_goals if g.category == "retirement"]
    projected_retirement = retirement_goals[0].target_amount if retirement_goals else 0.0

    assets_result = await session.execute(
        select(Asset).where(Asset.user_id == user.id, Asset.is_active.is_(True))
    )
    assets = list(assets_result.scalars().all())

    liabilities_result = await session.execute(
        select(Liability).where(Liability.user_id == user.id, Liability.is_active.is_(True))
    )
    liabilities = list(liabilities_result.scalars().all())

    income_result = await session.execute(
        select(IncomeSource).where(IncomeSource.user_id == user.id, IncomeSource.is_active.is_(True))
    )
    income_sources = list(income_result.scalars().all())

    expenses_result = await session.execute(
        select(Expense).where(Expense.user_id == user.id, Expense.is_active.is_(True))
    )
    expenses = list(expenses_result.scalars().all())

    total_assets = sum(a.current_value for a in assets)
    liquid_assets = sum(a.current_value for a in assets if a.asset_type in _LIQUID_ASSET_TYPES)
    invested_assets = sum(a.current_value for a in assets if a.asset_type in _INVESTED_ASSET_TYPES)
    total_liabilities = sum(lb.balance for lb in liabilities)

    annual_income = sum(i.annual_amount for i in income_sources)
    monthly_income = annual_income / 12
    monthly_expenses = sum(e.monthly_amount for e in expenses)

    savings_rate = 0.0
    if monthly_income > 0:
        savings_rate = max(0.0, (monthly_income - monthly_expenses) / monthly_income * 100)

    # Fall back to goal current amounts when no financial accounts have been entered yet
    if not assets and not liabilities:
        goal_total = sum(g.current_amount for g in active_goals)
        return DashboardResponse(
            net_worth=goal_total,
            net_worth_delta_pct=0.0,
            liquid_assets=0.0,
            invested=goal_total,
            liabilities=0.0,
            monthly_income=round(monthly_income, 2),
            monthly_expenses=round(monthly_expenses, 2),
            monthly_savings_rate=round(savings_rate, 1),
            projected_retirement=projected_retirement,
            plan_health_score=health,
            alerts=len(active_goals) - on_track_count,
            goal_count=len(active_goals),
            goals_on_track=on_track_count,
            suggestions=_generate_suggestions(active_goals, savings_rate),
        )

    return DashboardResponse(
        net_worth=total_assets - total_liabilities,
        net_worth_delta_pct=0.0,
        liquid_assets=liquid_assets,
        invested=invested_assets,
        liabilities=total_liabilities,
        monthly_income=round(monthly_income, 2),
        monthly_expenses=round(monthly_expenses, 2),
        monthly_savings_rate=round(savings_rate, 1),
        projected_retirement=projected_retirement,
        plan_health_score=health,
        alerts=len(active_goals) - on_track_count,
        goal_count=len(active_goals),
        goals_on_track=on_track_count,
        suggestions=_generate_suggestions(active_goals, savings_rate),
    )
