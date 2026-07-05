import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from app.services.monte_carlo import quick_probability_async

router = APIRouter(prefix="/goals", tags=["goals"])


def _years_to_goal(target_date: date) -> float:
    return max(0.1, (target_date - date.today()).days / 365.25)


async def _refresh_probability(goal: Goal) -> None:
    years = _years_to_goal(goal.target_date)
    goal.probability = round(
        await quick_probability_async(
            initial_amount=goal.current_amount,
            monthly_contribution=goal.monthly_contribution,
            years_to_goal=years,
            risk_profile=goal.risk_profile,
            target_amount=goal.target_amount,
        ),
        1,
    )
    goal.on_track = goal.probability >= 70.0


@router.get("", response_model=list[GoalResponse])
async def list_goals(
    category: str | None = Query(default=None),
    on_track: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Goal]:
    q = select(Goal).where(Goal.user_id == current_user.id, Goal.is_active.is_(True))
    if category:
        q = q.where(Goal.category == category)
    if on_track is not None:
        q = q.where(Goal.on_track.is_(on_track))
    result = await db.execute(q.order_by(Goal.priority.asc(), Goal.created_at.asc()))
    return list(result.scalars().all())


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    body: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    goal = Goal(
        user_id=current_user.id,
        **body.model_dump(),
    )
    await _refresh_probability(goal)
    db.add(goal)
    await db.flush()
    return goal


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    body: GoalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(goal, field, value)

    await _refresh_probability(goal)
    db.add(goal)
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    goal.is_active = False
    db.add(goal)
