import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FinancialAssumptions(Base):
    __tablename__ = "financial_assumptions"

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
    inflation_rate: Mapped[float] = mapped_column(Float, default=0.03, nullable=False)
    expected_return_conservative: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    expected_return_balanced: Mapped[float] = mapped_column(Float, default=0.07, nullable=False)
    expected_return_aggressive: Mapped[float] = mapped_column(Float, default=0.09, nullable=False)
    # DEPRECATED (2026-07-06, FutureCompatibilityAuditReport.md Finding C /
    # FoundationReconciliationReport.md): a flat, single-rate approximation
    # that predates the versioned `tax_regimes`/`tax_slabs` engine
    # (Milestone 1). Confirmed unread by any service/router as of this
    # reconciliation — grep shows it is only ever set to its default, never
    # computed against. `tax_slabs` (via `tax_regimes`) is the authoritative
    # source for any new tax calculation; do NOT wire new logic to this
    # field. See the migration plan in FoundationReconciliationReport.md.
    tax_rate: Mapped[float] = mapped_column(Float, default=0.22, nullable=False)
    retirement_age: Mapped[int] = mapped_column(Integer, default=65, nullable=False)
    social_security_monthly: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
