import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationSource
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    """Phase 3 (Notification Center). Pure read — computes every source
    fresh from existing engines/data and never writes a marker row itself
    (ArchitectureReview_Phase3.md)."""
    items, unread_count = await notification_service.list_notifications(db, current_user)
    return NotificationListResponse(items=items, unread_count=unread_count)


@router.post("/{source}/{dedupe_key}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    source: NotificationSource,
    dedupe_key: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await notification_service.mark_read(db, current_user, source, dedupe_key)


@router.post("/{source}/{dedupe_key}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_notification(
    source: NotificationSource,
    dedupe_key: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await notification_service.mark_dismissed(db, current_user, source, dedupe_key)
