from typing import Literal

from pydantic import BaseModel, Field

RecommendationSource = Literal["insurance", "schemes", "financial_health"]


class FamilyRecommendation(BaseModel):
    """Milestone 2 Task 11 — the shared envelope every aggregated
    recommendation is converted into, regardless of source. Every field is
    mandatory: no recommendation is ever returned with why/why_now/used/
    missing/confidence omitted (RecommendationIntegrityReview_Task11.md).
    `reference_code` grounds the recommendation in the specific verified
    fact it's based on (e.g. "80D", "SSY") — used only for conflict
    detection, never shown to the user as-is."""

    source: RecommendationSource
    recommendation_type: str
    subjects: list[str]
    reference_code: str
    why: str
    why_now: str
    what_information_was_used: list[str]
    what_information_is_missing: list[str]
    confidence_score: float = Field(ge=0, le=1)


class RecommendationConflict(BaseModel):
    """A genuine conflict: two recommendations sharing a subject AND a
    reference_code (competing for the same bounded deduction/scheme
    ceiling) — never merely 'same person, multiple recommendations'. See
    RecommendationConflictReview_Task11.md. Both recommendations remain in
    the response; this is additive context, never a suppression signal —
    no recommendation is ever hidden to 'resolve' a conflict."""

    subject: str
    reference_code: str
    sources: list[RecommendationSource]
    note: str


class FamilyRecommendationsResponse(BaseModel):
    recommendations: list[FamilyRecommendation]
    conflicts: list[RecommendationConflict]
