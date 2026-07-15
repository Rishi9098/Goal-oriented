import uuid
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.household import Dependent
from app.models.user import User
from app.schemas.family import (
    CoverageSummary,
    FamilyGoalSummary,
    FamilyHomeResponse,
    FamilyMemberCreate,
    FamilyMemberDetailResponse,
    FamilyMemberResponse,
    FamilyMemberSummary,
    HouseholdSummary,
    OnboardingSeedRequest,
    TaggedGoalSummary,
    TaggedMemberSummary,
)
from app.schemas.family import FamilyMemberUpdate as FamilyMemberUpdateSchema
from app.schemas.family_dashboard import FamilyDashboardResponse
from app.schemas.family_recommendations import FamilyRecommendationsResponse
from app.schemas.family_schemes import FamilySchemesResponse, SchemeEligibilityItem
from app.schemas.insurance import (
    CoverageUpdateRequest,
    FamilyInsuranceResponse,
    HealthPolicyCreate,
    HealthPolicyResponse,
    PolicyType,
)
from app.services import (
    family_dashboard_service,
    family_insurance_service,
    family_recommendations_service,
    family_service,
    scheme_eligibility_service,
)
from app.services.scheme_eligibility_service import EligibilityBucket

router = APIRouter(prefix="/family", tags=["family"])


async def _eligible_schemes_for(
    db: AsyncSession, member_name: str | None, dependent: Dependent
) -> list[dict[str, str]]:
    """Reuses Task 3's shared evaluation service (never duplicates the
    age/gender logic here) — currently only SSY has seeded eligibility
    rules, so this is the one check performed inline. Returns [] if the
    person doesn't match or isn't evaluable yet (e.g. no date_of_birth)."""
    result = await scheme_eligibility_service.check_ssy_eligibility(db, member_name, dependent)
    if result is None:
        return []
    return [{"code": result.scheme_code, "reason": result.reason}]


@router.post("/onboarding-seed", response_model=FamilyHomeResponse, status_code=status.HTTP_200_OK)
async def onboarding_seed(
    body: OnboardingSeedRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyHomeResponse:
    household = await family_service.seed_onboarding(db, current_user, body)
    members = await family_service.list_members_with_completeness(db, household)
    return FamilyHomeResponse(
        household=HouseholdSummary.model_validate(household),
        members=[
            FamilyMemberSummary(
                id=m["id"],
                relationship_type=m["relationship_type"],
                name=family_service.resolve_member_name(
                    m["relationship_type"], m["name"], current_user
                ),
                is_complete=m["is_complete"],
            )
            for m in members
        ],
    )


@router.get("", response_model=FamilyHomeResponse)
async def get_family_home(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyHomeResponse:
    # Lazy-provision fallback for pre-Milestone-2 accounts (no household row
    # yet) — an empty single-person household is a normal state, not a 404,
    # per FamilyPlanningDesign.md's empty-state design.
    household, _created = await family_service.get_or_create_household(db, current_user)
    members = await family_service.list_members_with_completeness(db, household)
    return FamilyHomeResponse(
        household=HouseholdSummary.model_validate(household),
        members=[
            FamilyMemberSummary(
                id=m["id"],
                relationship_type=m["relationship_type"],
                name=family_service.resolve_member_name(
                    m["relationship_type"], m["name"], current_user
                ),
                is_complete=m["is_complete"],
            )
            for m in members
        ],
    )


@router.post("/members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
async def create_family_member(
    body: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyMemberResponse:
    household, _created = await family_service.get_or_create_household(db, current_user)

    try:
        member, dependent = await family_service.create_member(db, current_user, household, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    eligible_schemes = await _eligible_schemes_for(db, member.name, dependent)

    return FamilyMemberResponse(
        id=member.id,
        household_id=member.household_id,
        relationship_type=member.relationship_type,
        name=member.name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        is_tax_dependent=body.is_tax_dependent,
        relationship_detail=body.relationship_detail,
        has_own_insurance=body.has_own_insurance,
        is_complete=family_service.is_complete(member, dependent),
        eligible_schemes=eligible_schemes,
    )


@router.put("/members/{member_id}", response_model=FamilyMemberResponse)
async def update_family_member(
    member_id: uuid.UUID,
    body: FamilyMemberUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyMemberResponse:
    household, _created = await family_service.get_or_create_household(db, current_user)

    found = await family_service.get_member_and_dependent(db, household, member_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    member, dependent = found

    if member.relationship_type == "self":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit the 'self' member via this endpoint",
        )

    try:
        member, dependent = await family_service.update_member(
            db, current_user, member, dependent, body
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    eligible_schemes = await _eligible_schemes_for(db, member.name, dependent)

    return FamilyMemberResponse(
        id=member.id,
        household_id=member.household_id,
        relationship_type=member.relationship_type,
        name=member.name,
        date_of_birth=dependent.date_of_birth,
        gender=dependent.gender,
        is_tax_dependent=dependent.is_tax_dependent,
        relationship_detail=dependent.relationship_detail,
        has_own_insurance=dependent.has_own_insurance,
        is_complete=family_service.is_complete(member, dependent),
        eligible_schemes=eligible_schemes,
    )


@router.get("/members/{member_id}", response_model=FamilyMemberDetailResponse)
async def get_family_member(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyMemberDetailResponse:
    household, _created = await family_service.get_or_create_household(db, current_user)

    found = await family_service.get_member_and_dependent(db, household, member_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    member, dependent = found

    tagged_goals, coverage = await family_service.get_member_detail(db, member)
    # Milestone 2 Task 9: get_family_member never populated eligible_schemes
    # (only create/update did) — the "self" member has no dependent row, so
    # this mirrors the same `if dependent else` guard already used for every
    # other dependent-derived field just below, rather than crashing on
    # scheme_eligibility_service's dependent.date_of_birth access.
    eligible_schemes = await _eligible_schemes_for(db, member.name, dependent) if dependent else []

    return FamilyMemberDetailResponse(
        member=FamilyMemberResponse(
            id=member.id,
            household_id=member.household_id,
            relationship_type=member.relationship_type,
            name=family_service.resolve_member_name(
                member.relationship_type, member.name, current_user
            ),
            date_of_birth=dependent.date_of_birth if dependent else None,
            gender=dependent.gender if dependent else None,
            is_tax_dependent=dependent.is_tax_dependent if dependent else None,
            relationship_detail=dependent.relationship_detail if dependent else None,
            has_own_insurance=dependent.has_own_insurance if dependent else None,
            is_complete=family_service.is_complete(member, dependent),
            eligible_schemes=eligible_schemes,
        ),
        tagged_goals=[TaggedGoalSummary(id=g.id, name=g.name) for g in tagged_goals],
        coverage=[
            CoverageSummary(health_policy_id=c["health_policy_id"], policy_type=c["policy_type"])
            for c in coverage
        ],
    )


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family_member(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    household, _created = await family_service.get_or_create_household(db, current_user)

    found = await family_service.get_member_and_dependent(db, household, member_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    member, dependent = found

    if member.relationship_type == "self":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the household creator"
        )

    # Reused by the Life Event Engine's Divorce handler — exactly one
    # implementation of "remove a family member (and its dependent)".
    await family_service.remove_member(db, current_user, member, dependent)


@router.get("/goals", response_model=list[FamilyGoalSummary])
async def list_family_goals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FamilyGoalSummary]:
    """Milestone 2 Task 8 — read-only. Reuses the caller's existing goals
    (family_service.list_goals_with_tags mirrors routers/goals.py's own
    list_goals() filter/ordering) plus the goal_household_members tag join;
    it does not recompute or duplicate anything routers/goals.py already
    owns."""
    goals_with_tags = await family_service.list_goals_with_tags(db, current_user)
    return [
        FamilyGoalSummary(
            id=goal.id,
            name=goal.name,
            category=goal.category,
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
            target_date=goal.target_date,
            probability=goal.probability,
            on_track=goal.on_track,
            tagged_members=[
                TaggedMemberSummary(
                    id=member.id,
                    name=family_service.resolve_member_name(
                        member.relationship_type, member.name, current_user
                    ),
                    relationship_type=member.relationship_type,
                )
                for member in members
            ],
        )
        for goal, members in goals_with_tags
    ]


@router.get("/insurance", response_model=FamilyInsuranceResponse)
async def get_family_insurance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyInsuranceResponse:
    """Milestone 2 Task 10. Read-only — the recommendation is computed
    fresh on every call (RecommendationIntegrityReview_Task10.md #4), never
    persisted, so this endpoint has no write side-effect despite computing
    a recommendation."""
    household, _created = await family_service.get_or_create_household(db, current_user)
    policies = await family_insurance_service.list_policies_with_coverage(db, current_user)
    recommendation = await family_insurance_service.compute_insurance_recommendation(
        db, current_user, household
    )
    return FamilyInsuranceResponse(
        policies=[
            HealthPolicyResponse(
                id=policy.id,
                policy_type=cast(PolicyType, policy.policy_type),
                sum_insured=policy.sum_insured,
                annual_premium=policy.annual_premium,
                insurer=policy.insurer,
                is_active=policy.is_active,
                covered_members=covered,
            )
            for policy, covered in policies
        ],
        recommendation=recommendation,
    )


@router.post(
    "/insurance/policies", response_model=HealthPolicyResponse, status_code=status.HTTP_201_CREATED
)
async def create_family_insurance_policy(
    body: HealthPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HealthPolicyResponse:
    household, _created = await family_service.get_or_create_household(db, current_user)
    try:
        policy, covered = await family_insurance_service.create_policy(
            db, current_user, household, body
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return HealthPolicyResponse(
        id=policy.id,
        policy_type=cast(PolicyType, policy.policy_type),
        sum_insured=policy.sum_insured,
        annual_premium=policy.annual_premium,
        insurer=policy.insurer,
        is_active=policy.is_active,
        covered_members=covered,
    )


@router.put("/insurance/policies/{policy_id}/coverage", response_model=HealthPolicyResponse)
async def update_family_insurance_policy_coverage(
    policy_id: uuid.UUID,
    body: CoverageUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HealthPolicyResponse:
    household, _created = await family_service.get_or_create_household(db, current_user)

    policy = await family_insurance_service.get_policy(db, current_user, policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    try:
        covered = await family_insurance_service.replace_policy_coverage(
            db, current_user, household, policy, body.household_member_ids
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return HealthPolicyResponse(
        id=policy.id,
        policy_type=cast(PolicyType, policy.policy_type),
        sum_insured=policy.sum_insured,
        annual_premium=policy.annual_premium,
        insurer=policy.insurer,
        is_active=policy.is_active,
        covered_members=covered,
    )


@router.get("/recommendations", response_model=FamilyRecommendationsResponse)
async def get_family_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyRecommendationsResponse:
    """Milestone 2 Task 11. Read-only aggregation over the existing
    insurance (Task 10) and scheme-eligibility (Task 3) engines — computed
    fresh on every call, nothing persisted (RecommendationIntegrityReview_
    Task11.md #3). Never duplicates either engine's own logic."""
    household, _created = await family_service.get_or_create_household(db, current_user)
    recommendations, conflicts = await family_recommendations_service.get_family_recommendations(
        db, current_user, household
    )
    return FamilyRecommendationsResponse(recommendations=recommendations, conflicts=conflicts)


@router.get("/dashboard", response_model=FamilyDashboardResponse)
async def get_family_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyDashboardResponse:
    """Milestone 2 Task 12. Read-only composition over existing services —
    six card payloads plus the Task 11 recommendations feed, computed fresh
    on every call, nothing persisted, no financial arithmetic in this layer
    (IntegrationIntegrityReview_Task12.md). Partial failures degrade to
    null cards rather than failing the whole dashboard."""
    household, _created = await family_service.get_or_create_household(db, current_user)
    return await family_dashboard_service.get_family_dashboard(db, current_user, household)


@router.get("/schemes", response_model=FamilySchemesResponse)
async def get_family_schemes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilySchemesResponse:
    """Milestone 2.1-P1. A direct passthrough of Task 3's already-certified
    evaluate_household_eligibility() — zero new eligibility logic, nothing
    persisted. See DesignReview_M2.1-P1.md."""
    household, _created = await family_service.get_or_create_household(db, current_user)
    buckets = await scheme_eligibility_service.evaluate_household_eligibility(db, household.id)

    def _to_items(bucket_name: EligibilityBucket) -> list[SchemeEligibilityItem]:
        return [
            SchemeEligibilityItem(
                scheme_code=r.scheme_code,
                scheme_name=r.scheme_name,
                member_name=r.member_name,
                reason=r.reason,
            )
            for r in buckets[bucket_name]
        ]

    return FamilySchemesResponse(
        eligible=_to_items("eligible"),
        potentially_eligible=_to_items("potentially_eligible"),
        not_eligible=_to_items("not_eligible"),
    )
