import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalCreate
from app.schemas.simulation import DashboardResponse, DashboardSuggestion
from app.services import life_event_service
from app.services.monte_carlo import quick_probability_async

settings = get_settings()

_LIQUID_ASSET_TYPES = frozenset({"checking", "savings", "money_market"})
_INVESTED_ASSET_TYPES = frozenset({"brokerage", "retirement_401k", "retirement_ira"})

# Extracted from _generate_suggestions' own inline `15` (Recommendation
# Engine v2, Phase C: RecommendationEngineV2.md §7 point 1 — "extract,
# don't duplicate" — this is the one place that document names as an
# intentional change to existing logic, not a new one). Same threshold,
# same value, now importable so family_recommendations_service's
# low_savings_rate rule reads the identical constant instead of a second,
# separately-typed `15`.
LOW_SAVINGS_RATE_THRESHOLD = 15.0

# The single source of truth for "what is the Calculation Context" (ADR-001).
# routers/goals.py's update_goal() checks incoming field names against this
# set to decide whether to recalculate — never duplicate this list there.
# Milestone 2 Task 9 added goals.custom_inflation_rate as a goal attribute
# that is deliberately NOT part of this set: it feeds a separate, on-the-fly
# future-cost projection (see Milestone2ImplementationContract.md §9), not
# the Monte Carlo probability engine, which remains Milestone 4 scope.
CALCULATION_CONTEXT_FIELDS = frozenset(
    {"current_amount", "monthly_contribution", "target_date", "risk_profile", "target_amount"}
)


async def calculate_goal_probability(goal: Goal) -> None:
    """
    The single, centralized Monte Carlo trigger for a goal's stored
    probability (ADR-001's Calculation Lifecycle). Call this only when a
    goal's Calculation Context — current_amount, monthly_contribution,
    target_date, risk_profile, target_amount — actually changes: goal
    creation and goal update (`routers/goals.py`). Never call this from a
    read path; every read (Dashboard, Reports, AI Copilot, Goals) must
    consume the value this function persisted, not recompute it.
    """
    years_to_goal = max(0.1, (goal.target_date - date.today()).days / 365.25)
    probability = await quick_probability_async(
        initial_amount=goal.current_amount,
        monthly_contribution=goal.monthly_contribution,
        years_to_goal=years_to_goal,
        risk_profile=goal.risk_profile,
        target_amount=goal.target_amount,
        seed=settings.monte_carlo_seed,
    )
    goal.probability = round(probability, 1)
    goal.on_track = probability >= 70.0


async def update_goal_fields(
    session: AsyncSession, user: User, goal_id: uuid.UUID, updates: dict[str, Any]
) -> tuple[Goal, dict[str, Any], dict[str, Any]]:
    """Applies a partial update to one of the user's goals — the exact
    mutation `PATCH /goals/{id}` already performs, including its
    conditional Monte Carlo recalculation (ADR-001: only when a
    Calculation Context field actually changed). That endpoint now calls
    this function too, so there is exactly one implementation — added for
    the Life Event Engine (Milestone 2), whose handlers need this same
    "update a goal, recalculate if warranted" mutation without going
    through an HTTP request. Returns the goal plus a before/after snapshot
    (via life_event_service.snapshot(), so a caller's LifeEventEffect uses
    the identical serialization undo's conflict check expects) of every
    field actually touched — including probability/on_track when a
    recalculation ran."""
    result = await session.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    snapshot_fields = set(updates.keys())
    recalculates = bool(CALCULATION_CONTEXT_FIELDS & updates.keys())
    if recalculates:
        snapshot_fields |= {"probability", "on_track"}

    before_state = life_event_service.snapshot(goal, snapshot_fields)
    for field, value in updates.items():
        setattr(goal, field, value)
    if recalculates:
        await calculate_goal_probability(goal)
    session.add(goal)
    await session.flush()
    await session.refresh(goal)
    after_state = life_event_service.snapshot(goal, snapshot_fields)
    return goal, before_state, after_state


async def create_goal(
    session: AsyncSession, user: User, data: GoalCreate
) -> tuple[Goal, dict[str, Any]]:
    """Creates a goal — the exact mutation `POST /goals` performs,
    including its unconditional Monte Carlo run on create (every new goal
    gets a probability, unlike update's conditional recalculation). That
    endpoint now calls this function too, so there is exactly one
    implementation — added for the Life Event Engine's optional
    goal-creation steps (e.g. Birth of Child's "start a college fund?").
    Returns the goal plus an after_state snapshot (via
    life_event_service.snapshot()) of every field just set plus the
    computed probability/on_track, for a caller building a "create"
    LifeEventEffect (before_state=None, per the engine's convention)."""
    goal = Goal(user_id=user.id, **data.model_dump())
    await calculate_goal_probability(goal)
    session.add(goal)
    await session.flush()
    fields = set(data.model_dump().keys()) | {"probability", "on_track"}
    after_state = life_event_service.snapshot(goal, fields)
    return goal, after_state


async def _active_goals(session: AsyncSession, user_id: "uuid.UUID | str") -> list[Goal]:
    """Read-only fetch — never mutates or persists a probability."""
    result = await session.execute(
        select(Goal).where(Goal.user_id == user_id, Goal.is_active.is_(True))
    )
    return list(result.scalars().all())


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
                impact=(
                    "Increasing monthly contributions could raise success probability above 70%."
                ),
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

    if 0 < savings_rate < LOW_SAVINGS_RATE_THRESHOLD:
        suggestions.append(DashboardSuggestion(
            id="low_savings_rate",
            title=(
                f"Savings rate is {savings_rate:.0f}% — below the "
                f"{LOW_SAVINGS_RATE_THRESHOLD:.0f}% target"
            ),
            impact="Review your monthly expenses to find areas to reduce spending.",
            severity="info",
        ))

    return suggestions[:5]


@dataclass(frozen=True)
class FinancialContext:
    """The single source of truth for every financial-facts aggregate this
    codebase computes — extracted from what get_dashboard() used to compute
    inline (Recommendation Engine v2, Phase A: RecommendationEngineV2.md
    §3, RecommendationEngineV2Validation.md item 1). get_dashboard is a
    consumer of this, not a second implementation of this math. All money
    fields are unrounded — each consumer applies its own display rounding,
    exactly as get_dashboard already did before this extraction."""

    monthly_income: float
    monthly_expenses: float
    monthly_savings: float
    savings_rate: float
    net_worth: float
    liquid_assets: float
    invested_assets: float
    total_assets: float
    total_liabilities: float
    debt_ratio: float
    # Phase B additions (RecommendationEngineV2Validation.md item 7's two
    # required corrections — nothing else was added, per that item's own
    # scope): the raw per-row liability list, since `high_interest_debt`
    # needs individual interest_rate/balance pairs, not just their sum; and
    # the most recent expense edit timestamp, since `expense_review_prompt`
    # needs a staleness signal the aggregate fields cannot provide. Neither
    # field is consumed anywhere yet — no rule reads them until Phase C.
    liabilities: list[Liability]
    expenses_last_updated_at: datetime | None
    # Phase C addition: a gap discovered while implementing the
    # already-approved `income_concentration` rule (RecommendationEngineV2.md
    # §6) — that rule needs a count of active income sources, which no
    # existing field provided. A count, not the full row list, is all it
    # needs, so that is all that was added (same minimal-extension
    # precedent as the two Phase B fields above).
    income_source_count: int


async def get_financial_context(
    session: AsyncSession, user: User, active_goals: list[Goal]
) -> FinancialContext:
    """
    `active_goals` must be the caller's already-fetched active Goal rows
    (get_dashboard already has these from `_active_goals`) — needed only to
    replicate the zero-assets-and-liabilities fallback below; this function
    issues no Goal query of its own, so passing them in costs nothing extra.
    """
    assets_result = await session.execute(
        select(Asset).where(Asset.user_id == user.id, Asset.is_active.is_(True))
    )
    assets = list(assets_result.scalars().all())

    liabilities_result = await session.execute(
        select(Liability).where(Liability.user_id == user.id, Liability.is_active.is_(True))
    )
    liabilities = list(liabilities_result.scalars().all())

    income_result = await session.execute(
        select(IncomeSource).where(
            IncomeSource.user_id == user.id, IncomeSource.is_active.is_(True)
        )
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
    monthly_savings = monthly_income - monthly_expenses

    savings_rate = 0.0
    if monthly_income > 0:
        savings_rate = max(0.0, (monthly_income - monthly_expenses) / monthly_income * 100)

    debt_ratio = 0.0
    if annual_income > 0:
        debt_ratio = total_liabilities / annual_income

    expenses_last_updated_at = max((e.updated_at for e in expenses), default=None)

    # Fall back to goal current amounts when no financial accounts have been
    # entered yet — preserved verbatim from get_dashboard's pre-extraction
    # behavior (RecommendationEngineV2Validation.md item 1's required
    # correction). `total_assets`/`total_liabilities` stay at their true,
    # honest value of 0 here (there really are zero rows); only
    # `net_worth`/`invested_assets` mirror get_dashboard's existing
    # goal-total stand-in, since those are the two fields get_dashboard's
    # response actually exposes and must match exactly.
    if not assets and not liabilities:
        goal_total = sum(g.current_amount for g in active_goals)
        return FinancialContext(
            monthly_income=monthly_income,
            monthly_expenses=monthly_expenses,
            monthly_savings=monthly_savings,
            savings_rate=savings_rate,
            net_worth=goal_total,
            liquid_assets=0.0,
            invested_assets=goal_total,
            total_assets=0.0,
            total_liabilities=0.0,
            debt_ratio=debt_ratio,
            liabilities=liabilities,
            expenses_last_updated_at=expenses_last_updated_at,
            income_source_count=len(income_sources),
        )

    return FinancialContext(
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        monthly_savings=monthly_savings,
        savings_rate=savings_rate,
        net_worth=total_assets - total_liabilities,
        liquid_assets=liquid_assets,
        invested_assets=invested_assets,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        debt_ratio=debt_ratio,
        liabilities=liabilities,
        expenses_last_updated_at=expenses_last_updated_at,
        income_source_count=len(income_sources),
    )


async def get_dashboard(session: AsyncSession, user: User) -> DashboardResponse:
    # Read-only: consumes each goal's already-persisted probability/on_track
    # (set only by calculate_goal_probability on create/update). Never
    # recomputes — see ADR-001.
    goals = await _active_goals(session, user.id)

    active_goals = [g for g in goals if g.is_active]
    on_track_count = sum(1 for g in active_goals if g.on_track)
    health = compute_plan_health(active_goals)

    retirement_goals = [g for g in active_goals if g.category == "retirement"]
    projected_retirement = retirement_goals[0].target_amount if retirement_goals else 0.0

    context = await get_financial_context(session, user, active_goals)

    return DashboardResponse(
        net_worth=context.net_worth,
        net_worth_delta_pct=0.0,
        liquid_assets=context.liquid_assets,
        invested=context.invested_assets,
        liabilities=context.total_liabilities,
        monthly_income=round(context.monthly_income, 2),
        monthly_expenses=round(context.monthly_expenses, 2),
        monthly_savings_rate=round(context.savings_rate, 1),
        projected_retirement=projected_retirement,
        plan_health_score=health,
        alerts=len(active_goals) - on_track_count,
        goal_count=len(active_goals),
        goals_on_track=on_track_count,
        suggestions=_generate_suggestions(active_goals, context.savings_rate),
    )
