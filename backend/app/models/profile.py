import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # DEPRECATED (2026-07-06, FutureCompatibilityAuditReport.md Finding A /
    # FoundationReconciliationReport.md): `household_members.relationship_type`
    # (a 'spouse' row's presence) is the authoritative source of marital
    # status going forward. This flat field is a convenience summary kept
    # only for onboarding-flow backward compatibility — do NOT write new
    # business logic (tax, eligibility, recommendation) against it. See the
    # migration plan in FoundationReconciliationReport.md before removing it.
    marital_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # DEPRECATED (2026-07-06, same rationale as `marital_status` above): the
    # `dependents` table (rows linked via `household_members`) is the
    # authoritative, entity-based source of dependent data going forward —
    # it carries date_of_birth/dependent_type/is_tax_dependent that this
    # integer count cannot. Do NOT write new business logic against this
    # field; it is not kept in sync with the `dependents` table.
    dependents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    employer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
