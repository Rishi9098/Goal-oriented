from datetime import datetime
from typing import Literal

from pydantic import BaseModel

NotificationSource = Literal[
    "insurance",
    "schemes",
    "family_member_added",
    "goal_at_risk",
    "goal_completed",
    "life_event",
    "divorce_review",
]
NotificationState = Literal["unread", "read"]


class NotificationItem(BaseModel):
    """A presentation-layer view of an existing fact — title/body are
    always derived live from the underlying engine or stored data at
    request time, never persisted (ArchitectureReview_Phase3.md)."""

    id: str
    source: NotificationSource
    title: str
    body: str
    action_path: str
    state: NotificationState
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int
