import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Government Policy Engine storage. Every numeric fact here (rate, limit,
# ceiling) is versioned with effective_from/effective_to rather than stored
# as a single current value — proven necessary by GovernmentPolicyReport.md:
# PPF/SSY/SCSS rates move quarterly, and the entire Income-tax Act is being
# replaced (1961 Act -> 2025 Act) this fiscal year with wholesale section
# renumbering (80C -> 123). See PolicyEngineReport.md for the full rationale.
#
# These tables are reference/versioned data, not user-owned mutable state,
# so they deliberately have no is_active soft-delete column — a superseded
# rate isn't "deleted," it simply has effective_to populated, which is
# itself the soft-delete-equivalent mechanism for versioned data.


class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    governing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    # "active" | "closed_to_new" | "sunset" — proven necessary by PMVVY
    # (closed to new subscribers since 31 March 2023) and SGB (discontinued
    # for new issuance since February 2024). A closed_to_new scheme must
    # never be recommended to a new user regardless of eligibility fit.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    rates: Mapped[list["SchemeRate"]] = relationship(
        "SchemeRate", back_populates="scheme", cascade="all, delete-orphan"
    )
    eligibility_rules: Mapped[list["SchemeEligibilityRule"]] = relationship(
        "SchemeEligibilityRule", back_populates="scheme", cascade="all, delete-orphan"
    )


class SchemeRate(Base):
    __tablename__ = "scheme_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # e.g. "interest_rate", "min_contribution", "max_contribution", "max_balance"
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_citation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="rates")


class SchemeEligibilityRule(Base):
    __tablename__ = "scheme_eligibility_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # e.g. "min_age", "max_age", "max_accounts_per_family", "taxpayer_status",
    # "residency_status" — a rule table rather than boolean columns, since
    # APY's "excluded if income-taxpayer" rule (GovernmentPolicyReport.md) is
    # qualitatively different from a simple age range and this shape
    # accommodates both without a schema change for the next unusual rule.
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False)  # eq, gte, lte, in
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="eligibility_rules")


class TaxAct(Base):
    __tablename__ = "tax_acts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sections: Mapped[list["TaxSection"]] = relationship(
        "TaxSection", back_populates="tax_act", cascade="all, delete-orphan"
    )


class TaxSection(Base):
    __tablename__ = "tax_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tax_act_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_acts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # e.g. "80C" under the 1961 Act, "123" under the 2025 Act for the same
    # deduction — GovernmentPolicyReport.md's single most important finding.
    section_number: Mapped[str] = mapped_column(String(20), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    limit_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tax_act: Mapped["TaxAct"] = relationship("TaxAct", back_populates="sections")


class TaxRegime(Base):
    __tablename__ = "tax_regimes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)  # "old" | "new"
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    slabs: Mapped[list["TaxSlab"]] = relationship(
        "TaxSlab", back_populates="tax_regime", cascade="all, delete-orphan"
    )


class TaxSlab(Base):
    __tablename__ = "tax_slabs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tax_regime_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_regimes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    income_from: Mapped[float] = mapped_column(Float, nullable=False)
    income_to: Mapped[float | None] = mapped_column(Float, nullable=True)  # null = no upper bound
    rate_percent: Mapped[float] = mapped_column(Float, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tax_regime: Mapped["TaxRegime"] = relationship("TaxRegime", back_populates="slabs")


class PolicyCitation(Base):
    __tablename__ = "policy_citations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tax_section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
