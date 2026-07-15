import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.household import HouseholdMember
    from app.models.user import User

# Modeled separately from the generic `assets` table rather than as another
# asset_type value: a floater policy's premium prices off the eldest covered
# member's age, and the family-vs-standalone-parent-policy tradeoff
# (FamilyHUFPlanningReport.md, with the doubled 80D/123 deduction) is a
# genuinely different calculation shape than a bank balance or investment
# holding.


class HealthPolicy(Base):
    __tablename__ = "health_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    primary_holder_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "family_floater" | "individual" | "senior_citizen_standalone"
    policy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sum_insured: Mapped[float] = mapped_column(Float, nullable=False)
    annual_premium: Mapped[float] = mapped_column(Float, nullable=False)
    insurer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    primary_holder: Mapped["User"] = relationship("User")
    coverage: Mapped[list["HealthPolicyCoverage"]] = relationship(
        "HealthPolicyCoverage", back_populates="health_policy", cascade="all, delete-orphan"
    )


class HealthPolicyCoverage(Base):
    __tablename__ = "health_policy_coverage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    health_policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("health_policies.id", ondelete="CASCADE"),
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

    health_policy: Mapped["HealthPolicy"] = relationship(
        "HealthPolicy", back_populates="coverage"
    )
    household_member: Mapped["HouseholdMember"] = relationship("HouseholdMember")
