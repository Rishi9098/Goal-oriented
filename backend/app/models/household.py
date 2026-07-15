import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User

# A household aggregates existing per-user financial data for a shared view;
# it never becomes the source of truth for any individual's data (goals,
# income, assets, etc. all stay keyed to user_id exactly as today). See
# DatabaseDesignReport.md Group A for the full rationale.


class Household(Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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

    created_by: Mapped["User"] = relationship("User")
    members: Mapped[list["HouseholdMember"]] = relationship(
        "HouseholdMember", back_populates="household", cascade="all, delete-orphan"
    )


class HouseholdMember(Base):
    __tablename__ = "household_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: a minor child or dependent parent may be a real planning
    # subject (e.g. the daughter a Sukanya Samriddhi Yojana goal is for)
    # without ever having their own login. See FamilyHUFPlanningReport.md.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Named relationship_type (not `relationship`) to avoid shadowing
    # SQLAlchemy's relationship() import in this module.
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Nullable, additive (Milestone 2 Task 2 blocker fix, 2026-07-06): the
    # only other source of a member's name is User.full_name via user_id,
    # but FamilyPlanningDesign.md deliberately gives a spouse/child/parent
    # no login this milestone (user_id stays NULL) — so this is the sole
    # place their name is stored. For relationship_type='self', this is
    # left NULL and the API falls back to the User's own full_name instead
    # of duplicating it.
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
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

    household: Mapped["Household"] = relationship("Household", back_populates="members")
    user: Mapped["User | None"] = relationship("User")
    dependent: Mapped["Dependent | None"] = relationship(
        "Dependent", back_populates="household_member", uselist=False, cascade="all, delete-orphan"
    )


class Dependent(Base):
    __tablename__ = "dependents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("household_members.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 'minor_child' | 'elderly_parent' | 'disabled_dependent' | 'other_dependent'
    # | 'spouse' (Milestone 2 Task 2: every non-self HouseholdMember gets
    # exactly one Dependent row, including spouse — corrected from
    # Milestone2ImplementationContract.md's original "not created for
    # spouse" note, which didn't account for date_of_birth having nowhere
    # else to live. See PROJECT_STATE.md's Task 2 entry.)
    dependent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_tax_dependent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Nullable, additive (Milestone 2 Task 2 blocker fix): drives the SSY
    # eligibility check for child-type dependents (female, age <10). Not
    # applicable to every dependent_type — enforced at the application
    # layer, not a DB constraint, matching has_own_insurance's convention.
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Nullable, additive: 'mother'|'father' for parent-type dependents, free
    # text for other-type dependents. Distinct from HouseholdMember's own
    # `relationship_type` (the coarse spouse/child/parent/other bucket) —
    # this is the specific sub-label within that bucket.
    relationship_detail: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Nullable, additive (Milestone2ImplementationContract.md §0.3):
    # 'yes' | 'no' | 'not_sure' | NULL (not yet asked / not applicable).
    # Captured for parent-type dependents to drive the Family Insurance
    # separate-policy recommendation (FamilyHUFPlanningReport.md's verified
    # doubled-deduction finding) — not applicable to every dependent_type,
    # enforced at the application layer, not a DB constraint.
    has_own_insurance: Mapped[str | None] = mapped_column(String(10), nullable=True)
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

    household_member: Mapped["HouseholdMember"] = relationship(
        "HouseholdMember", back_populates="dependent"
    )
