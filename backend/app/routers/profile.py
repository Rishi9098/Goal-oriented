from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.profile import UserProfileResponse, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.put("", response_model=UserProfileResponse)
async def upsert_profile(
    body: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    data = body.model_dump(exclude_unset=True)

    if profile is None:
        profile = UserProfile(user_id=current_user.id, **data)
        db.add(profile)
    else:
        for field, value in data.items():
            setattr(profile, field, value)
        db.add(profile)

    await db.flush()
    await db.refresh(profile)
    await db.commit()
    return profile
