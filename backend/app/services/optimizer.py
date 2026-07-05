"""
Financial optimization engine.

Given a goal that is below target probability, proposes a ranked list of
concrete actions (increase contribution, adjust risk profile, extend horizon)
that bring the plan above the requested confidence threshold.
"""

from dataclasses import dataclass

from app.schemas.simulation import OptimizationSuggestion
from app.services.monte_carlo import quick_probability

RISK_LADDER = ["conservative", "balanced", "aggressive"]


@dataclass
class GoalSnapshot:
    initial_amount: float
    monthly_contribution: float
    years_to_goal: float
    risk_profile: str
    target_amount: float
    current_probability: float


def _clamp_risk(profile: str, direction: int) -> str | None:
    idx = RISK_LADDER.index(profile)
    new_idx = idx + direction
    if 0 <= new_idx < len(RISK_LADDER):
        return RISK_LADDER[new_idx]
    return None


def generate_suggestions(
    snapshot: GoalSnapshot,
    *,
    target_probability: float = 80.0,
    max_monthly_increase: float = 1_000.0,
    allow_risk_adjustment: bool = True,
) -> list[OptimizationSuggestion]:
    """
    Return up to 5 ranked suggestions to raise success probability to
    `target_probability`.  Strategies explored (in priority order):

    1. Increase monthly contribution in $50 steps up to `max_monthly_increase`.
    2. Shift risk profile one level higher.
    3. Combine contribution increase + risk shift.
    4. Contribution increase alone (larger step) if risk shift is disallowed.
    """
    suggestions: list[OptimizationSuggestion] = []

    def _prob(contrib: float, profile: str) -> float:
        return quick_probability(
            initial_amount=snapshot.initial_amount,
            monthly_contribution=contrib,
            years_to_goal=snapshot.years_to_goal,
            risk_profile=profile,
            target_amount=snapshot.target_amount,
        )

    # Strategy 1: contribution increases
    for step in (50, 100, 200, 500):
        new_contrib = snapshot.monthly_contribution + step
        if new_contrib - snapshot.monthly_contribution > max_monthly_increase:
            break
        prob = _prob(new_contrib, snapshot.risk_profile)
        suggestions.append(
            OptimizationSuggestion(
                description=f"Increase monthly contribution by ${step:,.0f}",
                monthly_contribution_delta=step,
                risk_profile_change=None,
                projected_probability=prob,
                impact_summary=(
                    f"Raises success probability from "
                    f"{snapshot.current_probability:.0f}% to {prob:.0f}%."
                ),
            )
        )
        if prob >= target_probability:
            break  # minimum viable increase found

    # Strategy 2: risk profile shift
    if allow_risk_adjustment:
        higher_risk = _clamp_risk(snapshot.risk_profile, +1)
        if higher_risk:
            prob = _prob(snapshot.monthly_contribution, higher_risk)
            suggestions.append(
                OptimizationSuggestion(
                    description=f"Shift risk profile to {higher_risk.capitalize()}",
                    monthly_contribution_delta=0,
                    risk_profile_change=higher_risk,  # type: ignore[arg-type]
                    projected_probability=prob,
                    impact_summary=(
                        f"A {higher_risk} allocation targets higher long-term returns "
                        f"and raises this goal to {prob:.0f}% confidence."
                    ),
                )
            )

    # Strategy 3: combination
    if allow_risk_adjustment:
        higher_risk = _clamp_risk(snapshot.risk_profile, +1)
        combo_step = min(100.0, max_monthly_increase)
        if higher_risk and combo_step > 0:
            combo_contrib = snapshot.monthly_contribution + combo_step
            prob = _prob(combo_contrib, higher_risk)
            suggestions.append(
                OptimizationSuggestion(
                    description=(
                        f"Add $100/mo and shift to {higher_risk.capitalize()}"
                    ),
                    monthly_contribution_delta=combo_step,
                    risk_profile_change=higher_risk,  # type: ignore[arg-type]
                    projected_probability=prob,
                    impact_summary=(
                        f"Combined approach reaches {prob:.0f}% confidence with "
                        f"${combo_step:,.0f}/mo extra and a {higher_risk} allocation."
                    ),
                )
            )

    # Sort by projected probability descending, keep top 5
    suggestions.sort(key=lambda s: s.projected_probability, reverse=True)
    return suggestions[:5]
