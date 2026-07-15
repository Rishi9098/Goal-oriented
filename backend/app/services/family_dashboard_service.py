"""Family Dashboard composition — Milestone 2 Task 12.

A read-only composition layer: every figure is a persisted value or an
already-computed output of an existing certified service (Tasks 3/8/10/11
plus the money dashboard). This module contains zero financial arithmetic —
only counting, set membership, and min()-by-date selection. See
IntegrationIntegrityReview_Task12.md for the card-by-card source map.

Partial failures degrade gracefully: each section computes under its own
guard — a failure logs the full error (never silently swallowed) and
returns None for that card while every other section still populates.

Milestone 2.1-P4 (query optimization, PerformanceReview_M2.1-P4.md): the
household member list and the goal-with-tags list are each fetched exactly
once and shared by the two cards that need them (previously each card
re-queried independently). A shared-fetch failure degrades every card that
depends on it to None — identical to today's behavior, since a query that
fails once fails identically on an immediate retry within the same
request; this changes nothing observable, only how many times the same
data is asked for.
"""

from collections.abc import Coroutine
from datetime import date
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.goal import Goal
from app.models.household import Household, HouseholdMember
from app.models.user import User
from app.schemas.family_dashboard import (
    CoverageCard,
    DependentsCard,
    EducationCard,
    EmergencyCard,
    FamilyDashboardResponse,
    ParentsCard,
    RetirementCard,
)
from app.schemas.family_recommendations import FamilyRecommendation, RecommendationConflict
from app.services import (
    family_insurance_service,
    family_recommendations_service,
    family_service,
    planning_service,
)

logger = get_logger(__name__)

T = TypeVar("T")


async def _safe(section: str, computation: Coroutine[Any, Any, T]) -> T | None:
    """One failed card must not take the dashboard down: log with full
    context (never silently swallowed) and degrade that card to None."""
    try:
        return await computation
    except Exception as exc:
        logger.exception("family_dashboard_section_failed section=%s error=%s", section, exc)
        return None


async def _dependents_card(members: list[dict[str, Any]]) -> DependentsCard:
    counts = {"child": 0, "parent": 0, "spouse": 0}
    others = 0
    for m in members:
        rel = m["relationship_type"]
        if rel == "self":
            continue
        if rel in counts:
            counts[rel] += 1
        else:
            others += 1
    return DependentsCard(
        total_members=len(members),
        children=counts["child"],
        parents=counts["parent"],
        spouse=counts["spouse"],
        others=others,
    )


async def _education_card(
    user: User, goals_with_tags: list[tuple[Goal, list[HouseholdMember]]]
) -> EducationCard | None:
    today = date.today()
    # "Education costs ahead" — nearest future-dated education goal. A goal
    # whose target date has already passed is not "ahead"; if none are
    # future-dated the card shows its empty state rather than a stale date.
    upcoming = [
        (goal, tags)
        for goal, tags in goals_with_tags
        if goal.category == "education" and goal.target_date >= today
    ]
    if not upcoming:
        return None
    goal, tags = min(upcoming, key=lambda pair: pair[0].target_date)
    names = [
        resolved
        for member in tags
        if (
            resolved := family_service.resolve_member_name(
                member.relationship_type, member.name, user
            )
        )
    ]
    return EducationCard(
        goal_id=goal.id,
        goal_name=goal.name,
        target_date=goal.target_date,
        target_amount=goal.target_amount,
        tagged_member_names=names,
    )


async def _coverage_card(
    db: AsyncSession, user: User, members: list[dict[str, Any]]
) -> CoverageCard:
    policies = await family_insurance_service.list_policies_with_coverage(db, user)
    covered_ids = {
        covered.id for _policy, covered_members in policies for covered in covered_members
    }
    member_ids = {m["id"] for m in members}
    return CoverageCard(
        covered_members=len(covered_ids & member_ids),
        total_members=len(member_ids),
    )


async def _parents_card(db: AsyncSession, user: User, household: Household) -> ParentsCard:
    # The exact same authority the insurance recommendation uses — the
    # warning and the recommendation appear and disappear together
    # (DependencyValidation_Task12.md Finding 2).
    uncovered = await family_insurance_service.uncovered_parents(db, user, household)
    names = [
        family_service.resolve_member_name(member.relationship_type, member.name, user)
        or "A parent"
        for member, _dependent in uncovered
    ]
    return ParentsCard(uncovered_parent_names=names)


async def _retirement_card(
    goals_with_tags: list[tuple[Goal, list[HouseholdMember]]],
) -> RetirementCard | None:
    retirement = [g for g, _tags in goals_with_tags if g.category == "retirement"]
    if not retirement:
        return None
    # First by the list's existing ordering (priority asc, created asc) —
    # the same convention get_dashboard() uses for projected_retirement.
    goal = retirement[0]
    return RetirementCard(
        goal_id=goal.id,
        goal_name=goal.name,
        probability=goal.probability,
        on_track=goal.on_track,
    )


async def _emergency_card(db: AsyncSession, user: User) -> EmergencyCard:
    # get_dashboard() is documented read-only (ADR-001) — its figures are
    # passed through verbatim; the months-covered display is frontend
    # arithmetic per Task 9's precedent (DependencyValidation_Task12.md
    # Finding 1).
    dashboard = await planning_service.get_dashboard(db, user)
    return EmergencyCard(
        liquid_assets=dashboard.liquid_assets,
        monthly_expenses=dashboard.monthly_expenses,
    )


async def get_family_dashboard(
    db: AsyncSession, user: User, household: Household
) -> FamilyDashboardResponse:
    # Fetched once, shared by the two cards each needs it — see the
    # module-level Milestone 2.1-P4 note.
    members = await _safe(
        "members_list", family_service.list_members_with_completeness(db, household)
    )
    goals_with_tags = await _safe("goals_with_tags", family_service.list_goals_with_tags(db, user))

    dependents = (
        await _safe("dependents", _dependents_card(members)) if members is not None else None
    )
    education = (
        await _safe("education", _education_card(user, goals_with_tags))
        if goals_with_tags is not None
        else None
    )
    coverage = (
        await _safe("coverage", _coverage_card(db, user, members)) if members is not None else None
    )
    parents = await _safe("parents", _parents_card(db, user, household))
    retirement = (
        await _safe("retirement", _retirement_card(goals_with_tags))
        if goals_with_tags is not None
        else None
    )
    emergency = await _safe("emergency", _emergency_card(db, user))

    recommendations: list[FamilyRecommendation] = []
    conflicts: list[RecommendationConflict] = []
    recommendations_unavailable = False
    try:
        (
            recommendations,
            conflicts,
        ) = await family_recommendations_service.get_family_recommendations(db, user, household)
    except Exception as exc:
        logger.exception("family_dashboard_recommendations_failed error=%s", exc)
        recommendations_unavailable = True

    return FamilyDashboardResponse(
        dependents=dependents,
        education=education,
        coverage=coverage,
        parents=parents,
        retirement=retirement,
        emergency=emergency,
        recommendations=recommendations,
        conflicts=conflicts,
        recommendations_unavailable=recommendations_unavailable,
    )
