import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Layers 2 and 3 of the five-layer policy model in PolicyEngineReport.md.
# Layer 1 (government rules: schemes/scheme_rates/tax_*) was built in
# Milestone 1. This reconciliation adds the architectural support Layers
# 2-3 provide — structural storage only, no recommendation/ranking logic,
# no seeded rows. That logic belongs to the Recommendation Engine milestone;
# this migration only ensures the milestone doesn't need a schema change to
# start (FutureCompatibilityAuditReport.md Finding D).


class BestPracticeRule(Base):
    """Layer 2: financial-planning conventions that are not government law
    (e.g. "3-6 months emergency fund") and are not company-specific product
    decisions either. `confidence` distinguishes a verified, cited figure
    from mere industry convention from an internal, unverified heuristic —
    proven necessary by this engagement's own research surfacing all three
    states for different rules (see PolicyEngineReport.md, Layer 2)."""

    __tablename__ = "best_practice_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # Nullable: some rules are universal, some persona-specific
    # (UserPersonasReport.md's 11 personas).
    applies_to_persona: Mapped[str | None] = mapped_column(String(50), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rationale_text: Mapped[str] = mapped_column(Text, nullable=False)
    # "cfp_convention" | "verified_research" | "internal_heuristic"
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # "verified" | "convention" | "unverified_flag"
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    last_reviewed_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CompanyPolicy(Base):
    """Layer 3: Northstar's own product decisions layered on top of
    external fact (Layer 1) and convention (Layer 2) — e.g. "never
    recommend a closed_to_new scheme" is a company policy responding to a
    government fact, not the fact itself. `rule_definition` is JSON rather
    than a rigid FK-based structure since a policy may reference schemes,
    best-practice rules, or plain thresholds interchangeably, and this
    table's job (per Milestone 1's reconciliation) is to exist as
    structural support, not to encode any specific policy's logic."""

    __tablename__ = "company_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # "hard_gate" | "soft_preference" | "ranking_weight"
    policy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    rule_definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changelog_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
