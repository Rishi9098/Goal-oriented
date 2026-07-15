import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.financials import Asset
    from app.models.household import HouseholdMember
    from app.models.user import User


class HUFEntity(Base):
    """Hindu Undivided Family entity. FamilyHUFPlanningReport.md is explicit
    that HUF recommendations must be gated on a real funding source
    (ancestral property or family business income) — funding_source is a
    required, explicitly-enumerated field for exactly that reason, not free
    text."""

    __tablename__ = "huf_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    karta_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    huf_pan: Mapped[str | None] = mapped_column(String(10), nullable=True, unique=True)
    formation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    funding_source: Mapped[str] = mapped_column(String(50), nullable=False)
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

    karta: Mapped["User"] = relationship("User")
    coparceners: Mapped[list["HUFCoparcener"]] = relationship(
        "HUFCoparcener", back_populates="huf_entity", cascade="all, delete-orphan"
    )


class HUFCoparcener(Base):
    __tablename__ = "huf_coparceners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    huf_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("huf_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    household_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("household_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    became_coparcener_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    huf_entity: Mapped["HUFEntity"] = relationship("HUFEntity", back_populates="coparceners")
    household_member: Mapped["HouseholdMember"] = relationship("HouseholdMember")


class Nominee(Base):
    """Modeled per-asset with a percentage_share, mirroring SEBI's May 2026
    nomination rule (effective Sept 2026) directly: up to 3 nominees per
    demat/MF folio, each with a percentage split. Only name + relationship
    are required by the actual regulation (DOB only if a minor) — see
    FamilyHUFPlanningReport.md."""

    __tablename__ = "nominees"
    __table_args__ = (
        CheckConstraint(
            "percentage_share > 0 AND percentage_share <= 100",
            name="ck_nominees_percentage_share_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    percentage_share: Mapped[float] = mapped_column(Float, nullable=False)
    nominee_date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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

    asset: Mapped["Asset"] = relationship("Asset")


class EstateDocument(Base):
    """Stores only status, never document content — FamilyHUFPlanningReport.md
    is explicit that storing actual will content/legal text is out of scope
    for a financial-planning app."""

    __tablename__ = "estate_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    last_updated: Mapped[date | None] = mapped_column(Date, nullable=True)
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

    user: Mapped["User"] = relationship("User")
