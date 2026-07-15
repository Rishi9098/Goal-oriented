import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Purely descriptive tag: "this goal affects this household member." Never
# changes goals.user_id, which remains the sole owner of record for every
# purpose (tax attribution, contribution tracking, access control). This is
# explicitly not a joint-ownership model — see
# Milestone2ImplementationContract.md §0.1 and §8's mandatory disclosure
# requirement (goal detail screens must state the goal still belongs to one
# account). No relationship() back-references are added to Goal or
# HouseholdMember yet — that wiring belongs to the Family Goals tagging
# feature itself (ImplementationChecklist.md Task 8), not this schema-only
# migration (Task 1).


class GoalHouseholdMember(Base):
    __tablename__ = "goal_household_members"
    __table_args__ = (
        UniqueConstraint("goal_id", "household_member_id", name="uq_goal_household_members"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    household_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("household_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
