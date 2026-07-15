import uuid
from typing import Literal

from pydantic import BaseModel, Field

PolicyType = Literal["family_floater", "individual", "senior_citizen_standalone"]

_MAX_SUM_INSURED = 1_000_000_000.0
_MAX_ANNUAL_PREMIUM = 10_000_000.0


class CoveredMemberSummary(BaseModel):
    id: uuid.UUID
    name: str | None
    relationship_type: str


class HealthPolicyCreate(BaseModel):
    policy_type: PolicyType
    sum_insured: float = Field(gt=0, le=_MAX_SUM_INSURED)
    annual_premium: float = Field(ge=0, le=_MAX_ANNUAL_PREMIUM)
    insurer: str | None = Field(default=None, max_length=255)
    household_member_ids: list[uuid.UUID] = Field(min_length=1)


class CoverageUpdateRequest(BaseModel):
    household_member_ids: list[uuid.UUID] = Field(min_length=1)


class HealthPolicyResponse(BaseModel):
    id: uuid.UUID
    policy_type: PolicyType
    sum_insured: float
    annual_premium: float
    insurer: str | None
    is_active: bool
    covered_members: list[CoveredMemberSummary]


class InsuranceRecommendation(BaseModel):
    """Milestone 2 Task 10 — a calculation-lite fact application, not a
    Milestone 5 Recommendation Engine output. Computed fresh on every read
    (see RecommendationIntegrityReview_Task10.md #4) — never persisted to
    the `recommendations` table, so this is a plain response schema, not
    the `Recommendation` SQLAlchemy model."""

    recommendation_type: Literal["standalone_parent_policy"]
    # Milestone 2 Task 11: the household member name(s) this concerns —
    # already computed internally (the `names` this recommendation's why/
    # why_now text already names), exposed here so the Task 11 aggregation
    # layer can group/conflict-check without re-deriving who this is about.
    subjects: list[str]
    why: str
    why_now: str
    what_information_was_used: list[str]
    what_information_is_missing: list[str]
    floater_deduction_limit: float
    parent_deduction_limit: float
    confidence_score: float = Field(ge=0, le=1)


class FamilyInsuranceResponse(BaseModel):
    policies: list[HealthPolicyResponse]
    recommendation: InsuranceRecommendation | None
