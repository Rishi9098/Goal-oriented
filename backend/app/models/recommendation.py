import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.policy import Scheme, TaxSection
    from app.models.user import User

# The literal database representation of the explainable-AI requirement in
# AIArchitectureReport.md: every recommendation carries reasoning, a
# confidence score, alternatives considered, and assumptions used, as
# queryable structured data rather than text embedded in a chat reply.
# RecommendationCitation links a recommendation back to the exact
# scheme_rates/tax_sections rows it relied on, so a recommendation's
# grounding can be checked (or invalidated) if the underlying policy data
# later changes.


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # e.g. "scheme_suggestion", "risk_adjustment", "huf_eligibility",
    # "insurance_gap", "tax_regime_comparison", "goal_prioritization"
    recommendation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    alternatives_considered: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    assumptions_used: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
    citations: Mapped[list["RecommendationCitation"]] = relationship(
        "RecommendationCitation", back_populates="recommendation", cascade="all, delete-orphan"
    )


class RecommendationCitation(Base):
    __tablename__ = "recommendation_citations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=True
    )
    tax_section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_sections.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation", back_populates="citations"
    )
    scheme: Mapped["Scheme | None"] = relationship("Scheme")
    tax_section: Mapped["TaxSection | None"] = relationship("TaxSection")
