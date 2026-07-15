import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Phase 3 (Notification Center) — per ArchitectureReview_Phase3.md, this
# table stores ONLY seen/read/dismissed state, keyed by a stable,
# deterministically-derived identity (uuid5 of source + natural key — see
# NotificationIdentityReview.md). It never stores notification *content*:
# every notification's text is read live from the existing recommendation/
# goal/audit-log data at request time. This is the one property that keeps
# notifications a presentation layer, not a second recommendation engine.


class NotificationMarker(Base):
    __tablename__ = "notification_markers"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key", name="uq_notification_marker_user_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "insurance" | "schemes" | "family_member_added" | "goal_at_risk" | "goal_completed"
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    dedupe_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
