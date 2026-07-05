import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.goal import Goal
from app.models.simulation import Simulation
from app.models.user import User
from app.schemas.simulation import (
    OptimizationRequest,
    OptimizationResponse,
    PercentileOutcomes,
    SimulationRequest,
    SimulationResponse,
)
from app.services.monte_carlo import run_simulation_async
from app.services.optimizer import GoalSnapshot, generate_suggestions

settings = get_settings()

router = APIRouter(prefix="/simulate", tags=["simulate"])


@router.post("", response_model=SimulationResponse, status_code=201)
async def simulate(
    body: SimulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SimulationResponse:
    target_amount = (
        body.initial_amount + body.monthly_contribution * body.years_to_goal * 12
    )
    if body.goal_id is not None:
        goal_row = await db.execute(
            select(Goal).where(Goal.id == body.goal_id, Goal.user_id == current_user.id)
        )
        goal_obj = goal_row.scalar_one_or_none()
        if goal_obj is not None:
            target_amount = goal_obj.target_amount

    result = await run_simulation_async(
        initial_amount=body.initial_amount,
        monthly_contribution=body.monthly_contribution,
        years_to_goal=body.years_to_goal,
        risk_profile=body.risk_profile,
        target_amount=target_amount,
        num_simulations=min(body.num_simulations, settings.monte_carlo_simulations),
        seed=settings.monte_carlo_seed,
    )

    sim = Simulation(
        user_id=current_user.id,
        goal_id=body.goal_id,
        num_simulations=body.num_simulations,
        initial_amount=body.initial_amount,
        monthly_contribution=body.monthly_contribution,
        years_to_goal=body.years_to_goal,
        risk_profile=body.risk_profile,
        success_rate=result.success_rate,
        p10=result.p10,
        p25=result.p25,
        p50=result.p50,
        p75=result.p75,
        p90=result.p90,
        distribution=result.distribution,
    )
    db.add(sim)
    await db.flush()

    return SimulationResponse(
        id=sim.id,
        success_rate=result.success_rate,
        percentiles=PercentileOutcomes(
            p10=result.p10,
            p25=result.p25,
            p50=result.p50,
            p75=result.p75,
            p90=result.p90,
        ),
        distribution=result.distribution,
        created_at=sim.created_at,
    )


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize(
    body: OptimizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OptimizationResponse:
    result = await db.execute(
        select(Goal).where(Goal.id == body.goal_id, Goal.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    years = max(0.1, (goal.target_date - date.today()).days / 365.25)
    snapshot = GoalSnapshot(
        initial_amount=goal.current_amount,
        monthly_contribution=goal.monthly_contribution,
        years_to_goal=years,
        risk_profile=goal.risk_profile,
        target_amount=goal.target_amount,
        current_probability=goal.probability,
    )

    suggestions = generate_suggestions(
        snapshot,
        target_probability=body.target_probability,
        max_monthly_increase=body.max_monthly_increase,
        allow_risk_adjustment=body.allow_risk_adjustment,
    )

    return OptimizationResponse(
        goal_id=uuid.UUID(str(goal.id)),
        current_probability=goal.probability,
        suggestions=suggestions,
    )
