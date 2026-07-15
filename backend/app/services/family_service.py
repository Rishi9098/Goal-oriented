import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.goal import Goal
from app.models.goal_household_member import GoalHouseholdMember
from app.models.household import Dependent, Household, HouseholdMember
from app.models.insurance import HealthPolicy, HealthPolicyCoverage
from app.models.user import User
from app.schemas.family import FamilyMemberCreate, FamilyMemberUpdate, OnboardingSeedRequest

# relationship_type (coarse, HouseholdMember) -> dependent_type (Dependent).
# Every non-self member gets exactly one Dependent row — including spouse,
# since date_of_birth/gender have nowhere else to live. Corrected from
# Milestone2ImplementationContract.md's original "not created for spouse"
# assumption; see migration 008's docstring and PROJECT_STATE.md.
_DEPENDENT_TYPE_BY_RELATIONSHIP = {
    "spouse": "spouse",
    "child": "minor_child",
    "parent": "elderly_parent",
    "other": "other_dependent",
}


async def resolve_owned_household(db: AsyncSession, user: User) -> Household | None:
    """A user may act on a household if they created it, or (future
    milestone) are themselves a member of it. Written against the general
    rule now, per Milestone2ImplementationContract.md §2's ownership note,
    so it doesn't need rewriting when shared household access ships —
    though for Milestone 2 (no shared logins yet) this always resolves via
    created_by_user_id in practice."""
    result = await db.execute(
        select(Household)
        .outerjoin(
            HouseholdMember,
            (HouseholdMember.household_id == Household.id)
            & (HouseholdMember.user_id == user.id),
        )
        .where(
            Household.is_active.is_(True),
            (Household.created_by_user_id == user.id) | (HouseholdMember.id.is_not(None)),
        )
    )
    return result.scalars().first()


async def get_or_create_household(db: AsyncSession, user: User) -> tuple[Household, bool]:
    """Idempotent: returns (household, created). Used by both the
    onboarding-seed endpoint (explicit creation) and the Family Home
    endpoint's lazy-provision fallback for pre-Milestone-2 accounts."""
    existing = await resolve_owned_household(db, user)
    if existing is not None:
        return existing, False

    household = Household(name="My Household", created_by_user_id=user.id)
    db.add(household)
    await db.flush()

    self_member = HouseholdMember(
        household_id=household.id,
        user_id=user.id,
        relationship_type="self",
        name=None,  # resolved from User.full_name at read time, never duplicated
    )
    db.add(self_member)
    await db.flush()

    db.add(
        AuditLog(
            user_id=user.id,
            action="household_created",
            after_state={"household_id": str(household.id)},
        )
    )
    return household, True


async def seed_onboarding(
    db: AsyncSession, user: User, request: OnboardingSeedRequest
) -> Household:
    household, created = await get_or_create_household(db, user)
    if not created:
        # Idempotent re-entry (e.g. user re-enters onboarding) — do not
        # duplicate placeholder rows.
        return household

    if request.has_spouse:
        db.add(HouseholdMember(household_id=household.id, relationship_type="spouse"))
    if request.has_children:
        count = request.children_count or 0
        for _ in range(count):
            db.add(HouseholdMember(household_id=household.id, relationship_type="child"))
    if request.has_dependent_parents:
        db.add(HouseholdMember(household_id=household.id, relationship_type="parent"))
    await db.flush()

    return household


def is_complete(member: HouseholdMember, dependent: Dependent | None) -> bool:
    if member.relationship_type == "self":
        return True
    if not member.name:
        return False
    if member.relationship_type in ("spouse", "child"):
        return dependent is not None and dependent.date_of_birth is not None
    if member.relationship_type == "parent":
        return (
            dependent is not None
            and dependent.relationship_detail is not None
            and dependent.has_own_insurance is not None
        )
    if member.relationship_type == "other":
        return dependent is not None and bool(dependent.relationship_detail)
    return False


async def list_members_with_completeness(
    db: AsyncSession, household: Household
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(HouseholdMember, Dependent)
        .outerjoin(Dependent, Dependent.household_member_id == HouseholdMember.id)
        .where(HouseholdMember.household_id == household.id, HouseholdMember.is_active.is_(True))
        .order_by(HouseholdMember.created_at.asc())
    )
    rows = result.all()
    return [
        {
            "id": member.id,
            "relationship_type": member.relationship_type,
            "name": member.name,
            "is_complete": is_complete(member, dependent),
        }
        for member, dependent in rows
    ]


def validate_member_fields(
    relationship_type: str, fields: FamilyMemberCreate | FamilyMemberUpdate
) -> None:
    """Business-rule validation that depends on relationship_type, which
    Pydantic's per-field validators can't express cleanly since the same
    field (relationship_detail, date_of_birth) means something different,
    and is required or not, depending on the type. Raises ValueError; the
    router converts this to a 422."""
    if relationship_type in ("spouse", "child") and fields.date_of_birth is None:
        raise ValueError(f"date_of_birth is required for relationship_type={relationship_type}")

    if relationship_type == "parent":
        if fields.relationship_detail not in ("mother", "father"):
            raise ValueError("relationship_detail must be 'mother' or 'father' for a parent")
        if fields.has_own_insurance is None:
            raise ValueError("has_own_insurance is required for a parent")

    if relationship_type == "other" and not fields.relationship_detail:
        raise ValueError("relationship_detail is required for relationship_type=other")


async def create_member(
    db: AsyncSession, user: User, household: Household, body: FamilyMemberCreate
) -> tuple[HouseholdMember, Dependent]:
    validate_member_fields(body.relationship_type, body)

    member = HouseholdMember(
        household_id=household.id, relationship_type=body.relationship_type, name=body.name
    )
    db.add(member)
    await db.flush()

    dependent = Dependent(
        household_member_id=member.id,
        dependent_type=_DEPENDENT_TYPE_BY_RELATIONSHIP[body.relationship_type],
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        is_tax_dependent=body.is_tax_dependent,
        relationship_detail=body.relationship_detail,
        has_own_insurance=body.has_own_insurance,
    )
    db.add(dependent)
    await db.flush()

    db.add(
        AuditLog(
            user_id=user.id,
            action="family_member_added",
            after_state={
                "member_id": str(member.id),
                "relationship_type": member.relationship_type,
            },
        )
    )
    return member, dependent


async def get_member_and_dependent(
    db: AsyncSession, household: Household, member_id: uuid.UUID
) -> tuple[HouseholdMember, Dependent | None] | None:
    result = await db.execute(
        select(HouseholdMember, Dependent)
        .outerjoin(Dependent, Dependent.household_member_id == HouseholdMember.id)
        .where(
            HouseholdMember.id == member_id,
            HouseholdMember.household_id == household.id,
            HouseholdMember.is_active.is_(True),
        )
    )
    row = result.first()
    return (row[0], row[1]) if row is not None else None


async def update_member(
    db: AsyncSession,
    user: User,
    member: HouseholdMember,
    dependent: Dependent | None,
    body: FamilyMemberUpdate,
) -> tuple[HouseholdMember, Dependent]:
    validate_member_fields(member.relationship_type, body)

    before_state = {"name": member.name}
    member.name = body.name
    db.add(member)

    if dependent is None:
        dependent = Dependent(
            household_member_id=member.id,
            dependent_type=_DEPENDENT_TYPE_BY_RELATIONSHIP[member.relationship_type],
        )

    dependent.date_of_birth = body.date_of_birth
    dependent.gender = body.gender
    dependent.is_tax_dependent = body.is_tax_dependent
    dependent.relationship_detail = body.relationship_detail
    dependent.has_own_insurance = body.has_own_insurance
    db.add(dependent)
    await db.flush()

    db.add(
        AuditLog(
            user_id=user.id,
            action="family_member_updated",
            before_state=before_state,
            after_state={"name": member.name},
        )
    )
    return member, dependent


async def get_member_detail(
    db: AsyncSession, member: HouseholdMember
) -> tuple[list[Goal], list[dict[str, Any]]]:
    goals_result = await db.execute(
        select(Goal)
        .join(GoalHouseholdMember, GoalHouseholdMember.goal_id == Goal.id)
        .where(GoalHouseholdMember.household_member_id == member.id, Goal.is_active.is_(True))
    )
    tagged_goals = list(goals_result.scalars().all())

    coverage_result = await db.execute(
        select(HealthPolicyCoverage, HealthPolicy)
        .join(HealthPolicy, HealthPolicy.id == HealthPolicyCoverage.health_policy_id)
        .where(
            HealthPolicyCoverage.household_member_id == member.id,
            HealthPolicy.is_active.is_(True),
        )
    )
    coverage = [
        {"health_policy_id": policy.id, "policy_type": policy.policy_type}
        for _coverage_row, policy in coverage_result.all()
    ]
    return tagged_goals, coverage


async def remove_member(
    db: AsyncSession,
    user: User,
    member: HouseholdMember,
    dependent: Dependent | None = None,
) -> tuple[HouseholdMember, Dependent | None]:
    """Soft-deletes a household member and, if given, its cascading
    dependent — every non-self member has exactly one Dependent row (see
    this module's own `_DEPENDENT_TYPE_BY_RELATIONSHIP` comment), so
    removing the member without also deactivating its dependent would
    leave that invariant's "active" half orphaned. `dependent` is
    optional (default None) only because the one pre-existing caller,
    `DELETE /family/members/{id}`, already looks it up via
    `get_member_and_dependent` and can pass it straight through; the
    Life Event Engine's Divorce handler does the same. Returns both rows
    for a caller building `LifeEventEffect`s."""
    member.is_active = False
    db.add(member)
    if dependent is not None:
        dependent.is_active = False
        db.add(dependent)
    await db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="family_member_removed",
            before_state={"member_id": str(member.id)},
        )
    )
    return member, dependent


def resolve_member_name(relationship_type: str, name: str | None, user: User) -> str | None:
    """The 'self' member's name is never duplicated in household_members —
    it's resolved from the User record at read time. Moved here (was a
    private routers/family.py helper) so Milestone 2 Task 8's goal-tagging
    code can reuse the exact same resolution instead of a second copy."""
    return user.full_name if relationship_type == "self" else name


async def set_goal_household_tags(
    db: AsyncSession, user: User, goal: Goal, household_member_ids: list[uuid.UUID]
) -> list[HouseholdMember]:
    """Replaces the full 'who this affects' tag set for one goal in a
    single call (Milestone 2 Task 8). Never touches goal.user_id — a goal's
    owner is set once, at creation, by the existing goal-creation flow
    (routers/goals.py) and is never changed by this or any tagging
    operation; goal_household_members is a purely descriptive join table,
    not an ownership model (Milestone2ImplementationContract.md §0.1).
    Raises ValueError (the router converts this to 422) if any id doesn't
    belong to the caller's own household — reuses the same household
    resolution every other Family endpoint uses, not a second
    implementation."""
    household, _created = await get_or_create_household(db, user)

    valid_members: list[HouseholdMember] = []
    if household_member_ids:
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

    existing_result = await db.execute(
        select(GoalHouseholdMember.household_member_id).where(
            GoalHouseholdMember.goal_id == goal.id
        )
    )
    before_ids = [str(row) for row in existing_result.scalars().all()]

    await db.execute(delete(GoalHouseholdMember).where(GoalHouseholdMember.goal_id == goal.id))
    for member in valid_members:
        db.add(GoalHouseholdMember(goal_id=goal.id, household_member_id=member.id))
    await db.flush()

    db.add(
        AuditLog(
            user_id=user.id,
            action="family_goal_tag_changed",
            before_state={"goal_id": str(goal.id), "tagged_member_ids": before_ids},
            after_state={
                "goal_id": str(goal.id),
                "tagged_member_ids": [str(m.id) for m in valid_members],
            },
        )
    )
    return valid_members


async def list_goals_with_tags(
    db: AsyncSession, user: User
) -> list[tuple[Goal, list[HouseholdMember]]]:
    """Read-only — Milestone 2 Task 8's Family Goals screen. Reuses the
    caller's existing goals exactly as routers/goals.py's list_goals()
    already queries them (same filter, same ordering); this function only
    adds the tag join, it does not reimplement goal listing."""
    goals_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == user.id, Goal.is_active.is_(True))
        .order_by(Goal.priority.asc(), Goal.created_at.asc())
    )
    goals = list(goals_result.scalars().all())
    if not goals:
        return []

    goal_ids = [g.id for g in goals]
    tags_result = await db.execute(
        select(GoalHouseholdMember.goal_id, HouseholdMember)
        .join(HouseholdMember, HouseholdMember.id == GoalHouseholdMember.household_member_id)
        .where(GoalHouseholdMember.goal_id.in_(goal_ids), HouseholdMember.is_active.is_(True))
    )
    tags_by_goal: dict[uuid.UUID, list[HouseholdMember]] = {}
    for goal_id, member in tags_result.all():
        tags_by_goal.setdefault(goal_id, []).append(member)

    return [(g, tags_by_goal.get(g.id, [])) for g in goals]
