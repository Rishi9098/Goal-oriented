import uuid
from datetime import date

from pydantic import BaseModel

from app.schemas.family_recommendations import FamilyRecommendation, RecommendationConflict

# Milestone 2 Task 12 — every card payload is nullable at the response
# level: a section that fails to compute degrades to None (logged server-
# side) while the rest of the dashboard still populates. A null card is
# rendered as "unavailable", never as a zero that could be mistaken for a
# real figure (IntegrationIntegrityReview_Task12.md).


class DependentsCard(BaseModel):
    """Who depends on me? — counts by relationship type, from the same
    member snapshot the coverage card uses as its denominator."""

    total_members: int
    children: int
    parents: int
    spouse: int
    others: int


class EducationCard(BaseModel):
    """Education costs ahead — the education-category goal with the
    nearest target date, persisted values read out verbatim."""

    goal_id: uuid.UUID
    goal_name: str
    target_date: date
    target_amount: float
    tagged_member_names: list[str]


class CoverageCard(BaseModel):
    """Insurance coverage — N of M household members covered by any
    active policy on file."""

    covered_members: int
    total_members: int


class ParentsCard(BaseModel):
    """Parents — uncovered parents per the same authority the insurance
    recommendation uses (family_insurance_service.uncovered_parents), so
    this warning and the recommendation appear and disappear together."""

    uncovered_parent_names: list[str]


class RetirementCard(BaseModel):
    """Retirement readiness — the retirement goal's persisted probability,
    set only by the Calculation Lifecycle's write paths (ADR-001)."""

    goal_id: uuid.UUID
    goal_name: str
    probability: float
    on_track: bool


class EmergencyCard(BaseModel):
    """Emergency readiness — get_dashboard()'s authoritative figures
    passed through verbatim; the months-covered display is frontend
    arithmetic per Task 9's precedent (DependencyValidation_Task12.md
    Finding 1). No months figure is computed on the backend."""

    liquid_assets: float
    monthly_expenses: float


class FamilyDashboardResponse(BaseModel):
    dependents: DependentsCard | None
    education: EducationCard | None
    coverage: CoverageCard | None
    parents: ParentsCard | None
    retirement: RetirementCard | None
    emergency: EmergencyCard | None
    recommendations: list[FamilyRecommendation]
    conflicts: list[RecommendationConflict]
    # True when the feed computation itself failed — distinguishable from
    # the honest "no recommendations" empty state, so the frontend never
    # renders "you're all set" when the truth is "we couldn't check".
    recommendations_unavailable: bool = False
