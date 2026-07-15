import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User

# Milestone 2 — Life Event Engine, Phase A (Foundation only; no concrete
# event type is registered here — see app/services/life_event_service.py).
#
# A domain-specific specialization of the existing generic AuditLog
# before/after pattern (LifeEventEngineArchitecture.md §3), not a competing
# audit system: AuditLog remains the single-action generic ledger (a life
# event still writes one AuditLog row per record/undo, see
# life_event_service.py). life_events/life_event_effects exist because a
# single life event routinely touches more than one entity across up to
# nine different tables, and undo needs to reason about each touched row's
# safety independently — a capability a single JSON blob on one AuditLog
# row cannot provide.


class LifeEvent(Base):
    __tablename__ = "life_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="ux_life_events_user_idempotency_key"
        ),
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
    # Deliberately a free string, not a DB enum: Phase B+ will define actual
    # event_type values ("salary_raise", "marriage", ...) one at a time,
    # and a free string means adding a new one is never a migration —
    # mirrors income_sources.source_type / expenses.category's existing
    # convention, not goals.category's DB-enum convention.
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # The real-world date the user reports. Informational only — no
    # calculation in this codebase is date-of-event-aware
    # (LifeEventEngineArchitecture.md §4.3); this is never read by Monte
    # Carlo or any live-computed engine.
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # The exact inputs a handler was invoked with — re-displayable for
    # "Edit" (undo + re-record with corrected inputs, §7) and for audit.
    # Not the same thing as an effect's before/after row state.
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="applied")
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Optional, client-supplied. NULL never collides with another NULL
    # under standard SQL uniqueness semantics, so every event recorded
    # without one (every caller that doesn't pass idempotency_key) is
    # entirely unaffected by the UniqueConstraint above — see this
    # module's own docstring and migration 011.
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User")
    effects: Mapped[list["LifeEventEffect"]] = relationship(
        "LifeEventEffect",
        back_populates="life_event",
        cascade="all, delete-orphan",
        order_by="LifeEventEffect.created_at",
    )

    def __repr__(self) -> str:
        return f"<LifeEvent id={self.id} event_type={self.event_type} status={self.status}>"


class LifeEventEffect(Base):
    __tablename__ = "life_event_effects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    life_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("life_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Not a DB foreign key on purpose — one life event can touch rows across
    # nine different tables (goals, income_sources, expenses, assets,
    # liabilities, household_members, dependents, user_profiles,
    # financial_assumptions); a polymorphic FK isn't worth the complexity
    # for what is fundamentally an audit/undo pointer, not a relationship
    # the ORM itself needs to traverse.
    entity_table: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # "create" | "update" | "soft_delete" | "reactivate"
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # The touched row's own `updated_at` at the moment this effect was
    # recorded — a row-level fingerprint, not a duplicate of after_state.
    # Every one of the nine tables this engine touches already bumps
    # `updated_at` via `onupdate=func.now()` on *any* column change, so
    # this catches a row changed on a field this specific effect never
    # touched (LifeEventEngine_FinalReleaseAudit.md §1.3) without needing
    # to snapshot every column of every row. NULL for an entity type that
    # (hypothetically) has no `updated_at` column — undo degrades to the
    # pre-existing field-only check in that case, never raises.
    after_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    life_event: Mapped["LifeEvent"] = relationship("LifeEvent", back_populates="effects")

    def __repr__(self) -> str:
        return (
            f"<LifeEventEffect id={self.id} entity_table={self.entity_table} "
            f"change_type={self.change_type}>"
        )
