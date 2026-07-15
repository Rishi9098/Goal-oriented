import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.goal import Goal
from app.models.user import User
from app.schemas.family import FamilyTagsRequest, FamilyTagsResponse, TaggedMemberSummary
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from app.services import family_service, planning_service

router = APIRouter(prefix="/goals", tags=["goals"])


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
    # Reused by the Life Event Engine's optional goal-creation steps
    # (e.g. Birth of Child's "start a college fund?") — exactly one
    # implementation of "create a goal", not two.
    goal, _after_state = await planning_service.create_goal(db, current_user, body)
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
    # Reused by the Life Event Engine (Milestone 2) — any handler that
    # needs to touch a goal's Calculation Context fields calls
    # planning_service.update_goal_fields too, so there is exactly one
    # implementation of "update a goal, recalculate if ADR-001 warrants it".
    updates = body.model_dump(exclude_none=True)
    goal, _before_state, _after_state = await planning_service.update_goal_fields(
        db, current_user, goal_id, updates
    )
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


@router.put("/{goal_id}/family-tags", response_model=FamilyTagsResponse)
async def set_goal_family_tags(
    goal_id: uuid.UUID,
    body: FamilyTagsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyTagsResponse:
    """Milestone 2 Task 8. Replaces a goal's 'who this affects' tag set —
    goal.user_id is never read or written here; ownership is checked the
    same way every other goal endpoint on this router already does, and
    the tagging logic itself lives in family_service (reused, not
    duplicated) since it needs the same household-membership resolution
    every other Family endpoint uses."""
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    try:
        members = await family_service.set_goal_household_tags(
            db, current_user, goal, body.household_member_ids
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return FamilyTagsResponse(
        goal_id=goal.id,
        tagged_members=[
            TaggedMemberSummary(
                id=member.id,
                name=family_service.resolve_member_name(
                    member.relationship_type, member.name, current_user
                ),
                relationship_type=member.relationship_type,
            )
            for member in members
        ],
    )
