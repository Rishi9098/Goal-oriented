import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.household import Dependent, Household, HouseholdMember
from app.models.insurance import HealthPolicy, HealthPolicyCoverage
from app.models.policy import TaxSection
from app.models.user import User
from app.schemas.insurance import (
    CoveredMemberSummary,
    HealthPolicyCreate,
    InsuranceRecommendation,
)
from app.services import family_service
from app.services.scheme_eligibility_service import age_years

# Milestone 2 Task 10. This is a calculation-lite fact application citing
# FamilyHUFPlanningReport.md / GovernmentPolicyReport.md's verified 80D
# figures — deliberately not a Milestone 5 Recommendation Engine output.
# See RecommendationIntegrityReview_Task10.md for the full reasoning.

_SENIOR_CITIZEN_AGE = 60


async def _covered_members_for(
    db: AsyncSession, policy_id: uuid.UUID, user: User
) -> list[CoveredMemberSummary]:
    result = await db.execute(
        select(HouseholdMember)
        .join(HealthPolicyCoverage, HealthPolicyCoverage.household_member_id == HouseholdMember.id)
        .where(HealthPolicyCoverage.health_policy_id == policy_id)
    )
    members = list(result.scalars().all())
    return [
        CoveredMemberSummary(
            id=m.id,
            name=family_service.resolve_member_name(m.relationship_type, m.name, user),
            relationship_type=m.relationship_type,
        )
        for m in members
    ]


async def _covered_members_for_policies(
    db: AsyncSession, policy_ids: list[uuid.UUID], user: User
) -> dict[uuid.UUID, list[CoveredMemberSummary]]:
    """Batched form of _covered_members_for — one query across every
    policy_id instead of one query per policy (Milestone 2.1-P4 query
    optimization, PerformanceReview_M2.1-P4.md). Same per-member summary
    shape and content as calling _covered_members_for once per policy;
    only the number of round-trips changes."""
    if not policy_ids:
        return {}
    result = await db.execute(
        select(HealthPolicyCoverage.health_policy_id, HouseholdMember)
        .join(HouseholdMember, HealthPolicyCoverage.household_member_id == HouseholdMember.id)
        .where(HealthPolicyCoverage.health_policy_id.in_(policy_ids))
    )
    by_policy: dict[uuid.UUID, list[CoveredMemberSummary]] = {pid: [] for pid in policy_ids}
    for policy_id, member in result.all():
        by_policy[policy_id].append(
            CoveredMemberSummary(
                id=member.id,
                name=family_service.resolve_member_name(
                    member.relationship_type, member.name, user
                ),
                relationship_type=member.relationship_type,
            )
        )
    return by_policy


async def list_policies_with_coverage(
    db: AsyncSession, user: User
) -> list[tuple[HealthPolicy, list[CoveredMemberSummary]]]:
    result = await db.execute(
        select(HealthPolicy).where(
            HealthPolicy.primary_holder_user_id == user.id, HealthPolicy.is_active.is_(True)
        )
    )
    policies = list(result.scalars().all())
    coverage_by_policy = await _covered_members_for_policies(db, [p.id for p in policies], user)
    return [(p, coverage_by_policy[p.id]) for p in policies]


async def _validate_member_ids(
    db: AsyncSession, household: Household, household_member_ids: list[uuid.UUID]
) -> list[HouseholdMember]:
    result = await db.execute(
        select(HouseholdMember).where(
            HouseholdMember.id.in_(household_member_ids),
            HouseholdMember.household_id == household.id,
            HouseholdMember.is_active.is_(True),
        )
    )
    valid_members = list(result.scalars().all())
    valid_ids = {m.id for m in valid_members}
    invalid_ids = set(household_member_ids) - valid_ids
    if invalid_ids:
        raise ValueError(
            f"household_member_ids not in your household: {sorted(str(i) for i in invalid_ids)}"
        )
    return valid_members


async def create_policy(
    db: AsyncSession, user: User, household: Household, body: HealthPolicyCreate
) -> tuple[HealthPolicy, list[CoveredMemberSummary]]:
    members = await _validate_member_ids(db, household, body.household_member_ids)

    policy = HealthPolicy(
        primary_holder_user_id=user.id,
        policy_type=body.policy_type,
        sum_insured=body.sum_insured,
        annual_premium=body.annual_premium,
        insurer=body.insurer,
    )
    db.add(policy)
    await db.flush()

    for member in members:
        db.add(HealthPolicyCoverage(health_policy_id=policy.id, household_member_id=member.id))
    await db.flush()

    db.add(
        AuditLog(
            user_id=user.id,
            action="insurance_policy_created",
            after_state={
                "policy_id": str(policy.id),
                "policy_type": policy.policy_type,
                "sum_insured": policy.sum_insured,
                "annual_premium": policy.annual_premium,
                "covered_member_ids": [str(m.id) for m in members],
            },
        )
    )

    return policy, await _covered_members_for(db, policy.id, user)


async def get_policy(db: AsyncSession, user: User, policy_id: uuid.UUID) -> HealthPolicy | None:
    result = await db.execute(
        select(HealthPolicy).where(
            HealthPolicy.id == policy_id,
            HealthPolicy.primary_holder_user_id == user.id,
            HealthPolicy.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def replace_policy_coverage(
    db: AsyncSession,
    user: User,
    household: Household,
    policy: HealthPolicy,
    household_member_ids: list[uuid.UUID],
) -> list[CoveredMemberSummary]:
    """Replaces the full covered-member set for a policy in one call —
    mirrors the exact delete-then-reinsert pattern family_service.
    set_goal_household_tags() already established for goal tagging, rather
    than a second 'replace a set' implementation."""
    members = await _validate_member_ids(db, household, household_member_ids)

    before_ids_result = await db.execute(
        select(HealthPolicyCoverage.household_member_id).where(
            HealthPolicyCoverage.health_policy_id == policy.id
        )
    )
    before_ids = [str(m_id) for m_id in before_ids_result.scalars().all()]

    await db.execute(
        delete(HealthPolicyCoverage).where(HealthPolicyCoverage.health_policy_id == policy.id)
    )
    for member in members:
        db.add(HealthPolicyCoverage(health_policy_id=policy.id, household_member_id=member.id))
    await db.flush()

    db.add(
        AuditLog(
            user_id=user.id,
            action="insurance_policy_coverage_updated",
            before_state={"policy_id": str(policy.id), "covered_member_ids": before_ids},
            after_state={
                "policy_id": str(policy.id),
                "covered_member_ids": [str(m.id) for m in members],
            },
        )
    )

    return await _covered_members_for(db, policy.id, user)


async def _base_80d_limit(db: AsyncSession) -> float | None:
    """Reads the verified base figure from the seeded tax_sections table
    rather than a hardcoded literal — see RecommendationIntegrityReview_
    Task10.md #1. Returns None if the seed data isn't present; the caller
    must not fabricate a fallback number."""
    result = await db.execute(select(TaxSection).where(TaxSection.section_number == "80D"))
    section = result.scalars().first()
    return section.limit_amount if section else None


async def _covered_member_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    """Household-member IDs covered by any of the user's active policies —
    the single place this query lives (shared by uncovered_parents and
    compute_insurance_recommendation's what_used count)."""
    covered_ids_result = await db.execute(
        select(HealthPolicyCoverage.household_member_id)
        .join(HealthPolicy, HealthPolicy.id == HealthPolicyCoverage.health_policy_id)
        .where(HealthPolicy.primary_holder_user_id == user.id, HealthPolicy.is_active.is_(True))
    )
    return set(covered_ids_result.scalars().all())


async def uncovered_parents(
    db: AsyncSession,
    user: User,
    household: Household,
    *,
    covered_ids: set[uuid.UUID] | None = None,
) -> list[tuple[HouseholdMember, Dependent]]:
    """Complete parent-type members whose recorded insurance answer is not
    'yes' AND who are not covered by any active policy on file. Extracted
    from compute_insurance_recommendation (Milestone 2 Task 12) so the
    Family Dashboard's Parents card and the insurance recommendation share
    one authority and can never disagree — see DependencyValidation_
    Task12.md Finding 2. Pure read, no side effects.

    `covered_ids` is an optional pre-fetched value (Milestone 2.1-P4 query
    optimization) — when the caller already has it (compute_insurance_
    recommendation does), passing it in skips a redundant re-query of the
    same data. Callers that don't pass it (e.g. the Family Dashboard's
    Parents card) get the exact same query, behavior, and result as
    before — this parameter changes nothing observable, only whether the
    query runs once or twice."""
    rows_result = await db.execute(
        select(HouseholdMember, Dependent)
        .join(Dependent, Dependent.household_member_id == HouseholdMember.id)
        .where(
            HouseholdMember.household_id == household.id,
            HouseholdMember.is_active.is_(True),
            HouseholdMember.relationship_type == "parent",
        )
    )
    parent_rows = [
        (member, dependent)
        for member, dependent in rows_result.all()
        if family_service.is_complete(member, dependent)
    ]

    # Task 10's Business Rule names 'no'/'not_sure' explicitly; the
    # Acceptance Criteria's negative case ("all parents marked yes") implies
    # an unanswered value should also count — resolved in DataIntegrityReview_
    # Task10.md rather than picked silently.
    uninsured_parents = [
        (member, dependent)
        for member, dependent in parent_rows
        if dependent.has_own_insurance != "yes"
    ]
    if not uninsured_parents:
        return []

    # Exclude parents already covered by an active policy on file — the
    # has_own_insurance answer may be stale relative to a policy recorded
    # after onboarding; the actual coverage data is the more current signal.
    if covered_ids is None:
        covered_ids = await _covered_member_ids(db, user)
    return [
        (member, dependent)
        for member, dependent in uninsured_parents
        if member.id not in covered_ids
    ]


async def compute_insurance_recommendation(
    db: AsyncSession, user: User, household: Household
) -> InsuranceRecommendation | None:
    """A calculation-lite fact application — never a Milestone 5
    Recommendation Engine output, and never persisted (computed fresh on
    every read; see RecommendationIntegrityReview_Task10.md #4)."""
    base_limit = await _base_80d_limit(db)
    if base_limit is None:
        # Missing information must never produce a fabricated figure.
        return None

    # Fetched once and passed through — previously this same query ran a
    # second time immediately below (Milestone 2.1-P4 query optimization,
    # PerformanceReview_M2.1-P4.md). Same value, same result, one query.
    covered_ids = await _covered_member_ids(db, user)
    eligible = await uncovered_parents(db, user, household, covered_ids=covered_ids)
    if not eligible:
        return None

    as_of = date.today()
    names: list[str] = []
    what_used: list[str] = []
    what_missing: list[str] = []
    ages_known: list[int] = []

    for member, dependent in eligible:
        name = family_service.resolve_member_name(member.relationship_type, member.name, user) or (
            "This parent"
        )
        names.append(name)
        what_used.append(f"{name}'s recorded insurance status ('{dependent.has_own_insurance}')")
        if dependent.date_of_birth is not None:
            age = age_years(dependent.date_of_birth, as_of)
            ages_known.append(age)
            what_used.append(f"{name}'s date of birth (age {age})")
        else:
            what_missing.append(f"{name}'s date of birth")

    what_used.append(f"{len(covered_ids)} existing policy coverage record(s) on file")

    is_any_senior = any(age >= _SENIOR_CITIZEN_AGE for age in ages_known)
    parent_limit = base_limit * 2 if is_any_senior else base_limit
    any_age_unknown = bool(what_missing)

    who = names[0] if len(names) == 1 else " and ".join(names)
    is_are = "is" if len(names) == 1 else "are"

    why = (
        f"Adding {who} to a standalone health policy (or a new/existing family floater) "
        f"can unlock a tax deduction beyond what your own floater already covers."
    )
    if any_age_unknown:
        why += (
            f" The deduction could be as high as ₹{base_limit * 2:,.0f} if {who} "
            f"{'qualifies' if len(names) == 1 else 'qualify'} as a senior citizen — "
            f"not yet confirmed."
        )

    why_now = (
        f"{who} {is_are} not currently covered by any health policy you've recorded, "
        f"and {'their' if len(names) > 1 else 'the'} recorded insurance status is not 'yes'."
    )

    confidence = 1.0 if not any_age_unknown else 0.7

    return InsuranceRecommendation(
        recommendation_type="standalone_parent_policy",
        subjects=names,
        why=why,
        why_now=why_now,
        what_information_was_used=what_used,
        what_information_is_missing=what_missing,
        floater_deduction_limit=base_limit,
        parent_deduction_limit=parent_limit,
        confidence_score=confidence,
    )
