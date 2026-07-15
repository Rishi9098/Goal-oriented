"""Service layer for the user profile entity.

Job Change (Life Event Engine) needs the exact create-or-update
semantics `PUT /profile` performs, but scoped to just the fields a
handler is touching (e.g. `employer`/`occupation`) rather than a full
request body — so this extraction is parameterized on a plain dict
instead of the `UserProfileUpdate` schema class the router uses.
`routers/profile.py`'s `upsert_profile` now calls this too, so there is
exactly one implementation of "create-or-update a profile."
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import UserProfile
from app.models.user import User
from app.services import life_event_service


async def update_profile_fields(
    db: AsyncSession, user: User, updates: dict[str, Any]
) -> tuple[UserProfile, dict[str, Any] | None, dict[str, Any]]:
    """Creates the profile if none exists yet, otherwise updates only the
    given fields — the exact create-or-update mutation `PUT /profile`
    already performs. Returns the profile, before_state (None when this
    call created the profile — a "create" effect has no before_state, per
    the Life Event Engine's convention) and after_state, both built via
    `life_event_service.snapshot()` over only the fields this call
    touched."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(user_id=user.id, **updates)
        db.add(profile)
        await db.flush()
        await db.refresh(profile)
        after_state = life_event_service.snapshot(profile, updates.keys())
        return profile, None, after_state

    before_state = life_event_service.snapshot(profile, updates.keys())
    for field, value in updates.items():
        setattr(profile, field, value)
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    after_state = life_event_service.snapshot(profile, updates.keys())
    return profile, before_state, after_state
