import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.estate import Nominee
from app.models.financials import Asset
from app.models.goal import Goal
from app.models.household import Household, HouseholdMember
from app.models.insurance import HealthPolicy, HealthPolicyCoverage
from app.models.life_event import LifeEvent
from app.models.notification import NotificationMarker
from app.models.user import User
from app.schemas.notification import NotificationItem, NotificationSource
from app.services import family_insurance_service, family_service, scheme_eligibility_service

# Fixed, arbitrary namespace UUID for this feature's uuid5 identities — see
# NotificationIdentityReview.md. Must never change once in production: doing
# so would silently reset every user's read/dismissed state.
_NAMESPACE = uuid.UUID("6f6a1b6e-6b8a-4b6b-9b1a-9b6a6b8a6b6b")

# "Family member added" is sourced from real events (AuditLog rows), so it
# needs a recency window to read as a notification rather than a permanent
# household history — see NotificationIdentityReview.md.
_FAMILY_MEMBER_ADDED_WINDOW_DAYS = 30
_GOAL_ON_TRACK_THRESHOLD = 70.0

# Same rationale as _FAMILY_MEMBER_ADDED_WINDOW_DAYS: a life event is a real,
# dated occurrence (life_events.recorded_at), so it needs a recency window
# to read as a notification rather than a permanent history — see
# LifeEventEngineArchitecture.md §6.
_LIFE_EVENT_WINDOW_DAYS = 30

# The only "per-event" content this file contains — one-line title/body
# templates per event_type, not a second notification mechanism
# (LifeEventEngineArchitecture.md §6: "one new collector... turns each
# into one _Fact using event_type-specific title/body templates"). Each
# Life Event Engine handler adds exactly one entry here, never a new
# collector function.
_LIFE_EVENT_COPY: dict[str, tuple[str, str]] = {
    "loan_payoff": ("✓ Debt paid off", "One of your liabilities has been closed."),
    "salary_raise": ("💰 Salary updated", "One of your income sources has been updated."),
    "job_change": ("💼 Job change recorded", "Your employer and income have been updated."),
    "bonus": ("🎉 Bonus recorded", "A one-time bonus has been added to your assets."),
    "new_loan": ("📋 New loan recorded", "A new liability has been added to your plan."),
    "house_purchase": (
        "🏠 Home purchase recorded",
        "Your new home and mortgage have been added to your plan.",
    ),
    "home_sale": ("🏡 Home sale recorded", "Your home sale proceeds have been added to your plan."),
    "divorce": ("Divorce recorded", "Your household and financial plan have been updated."),
    "retirement": (
        "🎉 Retirement recorded",
        "Congratulations on your retirement! Your plan has been updated.",
    ),
    "education_planning": (
        "🎓 Education goal created",
        "A new education goal has been added to your plan.",
    ),
    "inheritance": ("Inheritance recorded", "A new asset has been added to your plan."),
    "major_medical_event": (
        "Medical expense recorded",
        "A healthcare expense has been added to your plan.",
    ),
    "business_start": ("Business start recorded", "Your employment status has been updated."),
    "business_sale": ("Business sale recorded", "Your sale proceeds have been added to your plan."),
}
_LIFE_EVENT_DEFAULT_COPY = ("Life event recorded", "Your financial plan has been updated.")

# Event types whose handler already gets a free notification through a
# pre-existing, non-generic collector (e.g. Marriage's household-member
# create already fires `_collect_family_member_added_facts` via
# `family_service.create_member`'s own "family_member_added" AuditLog row
# — LifeEventEngineArchitecture.md §5.3's "Notifications: Free"). Without
# this exclusion, `_collect_life_event_facts` below would also produce a
# second, redundant notification for the same real-world action, since it
# reads every `life_events` row unconditionally. Add an event_type here
# only when its handler's own underlying write already has a dedicated,
# pre-existing collector — not as a way to silence a notification that
# should otherwise appear.
_LIFE_EVENT_SKIP_TYPES = frozenset(
    {"marriage", "birth_of_child", "adoption", "dependent_parent"}
)


def _dedupe_key(source: str, natural_key: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"{source}:{natural_key}")


def _aware(dt: datetime) -> datetime:
    """SQLite (test DB) returns naive datetimes even for TIMESTAMPTZ
    columns, unlike Postgres (production) — normalize so sorting never
    compares naive against aware values."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@dataclass(frozen=True)
class _Fact:
    dedupe_key: uuid.UUID
    source: NotificationSource
    title: str
    body: str
    action_path: str
    event_at: datetime | None  # real event/update time, when one exists


async def _collect_insurance_fact(
    db: AsyncSession, user: User, household: Household
) -> _Fact | None:
    """Reads family_insurance_service.compute_insurance_recommendation()
    exactly as /family/insurance already does — zero new calculation
    (DependencyValidation_Phase3.md #1)."""
    rec = await family_insurance_service.compute_insurance_recommendation(db, user, household)
    if rec is None:
        return None
    subjects_key = ",".join(sorted(rec.subjects))
    return _Fact(
        dedupe_key=_dedupe_key("insurance", f"{user.id}:{subjects_key}"),
        source="insurance",
        title=f"Insurance recommendation for {', '.join(rec.subjects)}",
        body=rec.why,
        action_path="/app/family/insurance",
        event_at=None,
    )


async def _collect_scheme_facts(
    db: AsyncSession, user: User, household_id: uuid.UUID
) -> list[_Fact]:
    """Reads scheme_eligibility_service.evaluate_household_eligibility()
    exactly as /family/schemes already does — zero new calculation."""
    buckets = await scheme_eligibility_service.evaluate_household_eligibility(db, household_id)
    facts = []
    for item in buckets["eligible"] + buckets["potentially_eligible"]:
        who = item.member_name or "your household"
        facts.append(
            _Fact(
                dedupe_key=_dedupe_key(
                    "schemes", f"{user.id}:{item.scheme_code}:{item.member_name or ''}"
                ),
                source="schemes",
                title=f"{item.scheme_name} — {who}",
                body=item.reason,
                action_path="/app/family/schemes",
                event_at=None,
            )
        )
    return facts


async def _collect_family_member_added_facts(db: AsyncSession, user: User) -> list[_Fact]:
    """Reads existing AuditLog rows — zero new calculation, and the only
    source with a real event timestamp available for free. The audit
    row's own after_state carries only member_id/relationship_type (see
    family_service.py), not a name, so the current name is read from the
    HouseholdMember row itself — still a plain read of existing data, not a
    new computation."""
    cutoff = datetime.now(UTC) - timedelta(days=_FAMILY_MEMBER_ADDED_WINDOW_DAYS)
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.user_id == user.id,
            AuditLog.action == "family_member_added",
            AuditLog.created_at >= cutoff,
        )
        .order_by(AuditLog.created_at.desc())
    )
    facts = []
    for row in result.scalars().all():
        member_id = (row.after_state or {}).get("member_id")
        if member_id is None:
            continue
        member = await db.get(HouseholdMember, uuid.UUID(member_id))
        if member is None:
            continue  # removed since — nothing to notify about
        name = family_service.resolve_member_name(member.relationship_type, member.name, user) or (
            f"A new {member.relationship_type}"
        )
        facts.append(
            _Fact(
                dedupe_key=_dedupe_key("family_member_added", str(row.id)),
                source="family_member_added",
                title=f"{name} was added to your household",
                body="Review their profile to complete tax and insurance details.",
                action_path="/app/family",
                event_at=_aware(row.created_at),
            )
        )
    return facts


async def _collect_goal_facts(db: AsyncSession, user: User) -> list[_Fact]:
    """Reads goal.on_track / goal.current_amount / goal.target_amount —
    already-stored, already-computed values (ADR-001); no Monte Carlo
    re-run, no new calculation."""
    result = await db.execute(
        select(Goal).where(Goal.user_id == user.id, Goal.is_active.is_(True))
    )
    facts = []
    for goal in result.scalars().all():
        if goal.current_amount >= goal.target_amount:
            facts.append(
                _Fact(
                    dedupe_key=_dedupe_key("goal_completed", f"{goal.id}:completed"),
                    source="goal_completed",
                    title=f"✓ {goal.name} is fully funded",
                    body=f"You've reached your target of ₹{goal.target_amount:,.0f}.",
                    action_path="/app/goals",
                    event_at=_aware(goal.updated_at),
                )
            )
        elif not goal.on_track:
            facts.append(
                _Fact(
                    dedupe_key=_dedupe_key("goal_at_risk", f"{goal.id}:at_risk"),
                    source="goal_at_risk",
                    title=f"{goal.name} is at risk",
                    body=(
                        f"Current probability of success is {goal.probability:.0f}%, "
                        f"below the {_GOAL_ON_TRACK_THRESHOLD:.0f}% on-track threshold."
                    ),
                    action_path="/app/goals",
                    event_at=_aware(goal.updated_at),
                )
            )
    return facts


async def _collect_life_event_facts(db: AsyncSession, user: User) -> list[_Fact]:
    """Reads life_events rows directly — zero new calculation, mirroring
    _collect_family_member_added_facts's real-event-timestamp pattern. One
    collector for every Life Event Engine event type, present or future —
    adding a new event type is one _LIFE_EVENT_COPY entry, never a new
    collector."""
    cutoff = datetime.now(UTC) - timedelta(days=_LIFE_EVENT_WINDOW_DAYS)
    result = await db.execute(
        select(LifeEvent)
        .where(
            LifeEvent.user_id == user.id,
            LifeEvent.status == "applied",
            LifeEvent.is_active.is_(True),
            LifeEvent.recorded_at >= cutoff,
            LifeEvent.event_type.notin_(_LIFE_EVENT_SKIP_TYPES),
        )
        .order_by(LifeEvent.recorded_at.desc())
    )
    facts = []
    for life_event in result.scalars().all():
        title, body = _LIFE_EVENT_COPY.get(life_event.event_type, _LIFE_EVENT_DEFAULT_COPY)
        facts.append(
            _Fact(
                dedupe_key=_dedupe_key("life_event", str(life_event.id)),
                source="life_event",
                title=title,
                body=body,
                action_path="/app/life-events",
                event_at=_aware(life_event.recorded_at),
            )
        )
    return facts


async def _collect_divorce_review_facts(db: AsyncSession, user: User) -> list[_Fact]:
    """Two purely-live "review" prompts for Divorce
    (LifeEventEngineArchitecture.md §5.4) — no persistence, no new stored
    fact, the same philosophy as _collect_insurance_fact/
    _collect_scheme_facts (event_at=None, no recency window: these are
    "you still need to fix this" prompts, not "something just happened"
    ones). Both are scoped to an inactive spouse-typed HouseholdMember
    existing at all — not just "any active spouse-designated Nominee" as
    §5.4's own prose reads literally — so a currently-married user with
    an active spouse nominee is never nagged; only someone whose spouse
    relationship has actually ended (via Divorce, or any other path that
    deactivates a spouse-typed member) sees these."""
    result = await db.execute(
        select(HouseholdMember).where(
            HouseholdMember.household_id.in_(
                select(Household.id).where(Household.created_by_user_id == user.id)
            ),
            HouseholdMember.relationship_type == "spouse",
            HouseholdMember.is_active.is_(False),
        )
    )
    inactive_spouses = list(result.scalars().all())
    if not inactive_spouses:
        return []

    facts: list[_Fact] = []

    coverage_result = await db.execute(
        select(HealthPolicyCoverage, HouseholdMember)
        .join(HouseholdMember, HouseholdMember.id == HealthPolicyCoverage.household_member_id)
        .join(HealthPolicy, HealthPolicy.id == HealthPolicyCoverage.health_policy_id)
        .where(
            HouseholdMember.id.in_([m.id for m in inactive_spouses]),
            HealthPolicy.is_active.is_(True),
            HealthPolicy.primary_holder_user_id == user.id,
        )
    )
    for coverage, member in coverage_result.all():
        facts.append(
            _Fact(
                dedupe_key=_dedupe_key("divorce_review_insurance", str(coverage.id)),
                source="divorce_review",
                title=f"Review insurance coverage for {member.name}",
                body="This person is still listed on an active health policy.",
                action_path="/app/family/insurance",
                event_at=None,
            )
        )

    nominee_result = await db.execute(
        select(Nominee)
        .join(Asset, Asset.id == Nominee.asset_id)
        .where(
            Asset.user_id == user.id,
            Asset.is_active.is_(True),
            Nominee.is_active.is_(True),
            Nominee.relationship_type == "spouse",
        )
    )
    for nominee in nominee_result.scalars().all():
        facts.append(
            _Fact(
                dedupe_key=_dedupe_key("divorce_review_nominee", str(nominee.id)),
                source="divorce_review",
                title="Review beneficiary/nominee designations",
                body=f"{nominee.name} is still listed as a spouse nominee on one of your assets.",
                action_path="/app/estate",
                event_at=None,
            )
        )
    return facts


async def _collect_facts(db: AsyncSession, user: User) -> list[_Fact]:
    household, _created = await family_service.get_or_create_household(db, user)
    facts: list[_Fact] = []
    insurance_fact = await _collect_insurance_fact(db, user, household)
    if insurance_fact is not None:
        facts.append(insurance_fact)
    facts.extend(await _collect_scheme_facts(db, user, household.id))
    facts.extend(await _collect_family_member_added_facts(db, user))
    facts.extend(await _collect_goal_facts(db, user))
    facts.extend(await _collect_life_event_facts(db, user))
    facts.extend(await _collect_divorce_review_facts(db, user))
    return facts


async def list_notifications(db: AsyncSession, user: User) -> tuple[list[NotificationItem], int]:
    """Pure read: computes every source fresh, left-joins against existing
    markers, creates nothing. See ArchitectureReview_Phase3.md's read/write
    discipline section — this endpoint must never mutate state."""
    facts = await _collect_facts(db, user)
    markers_by_key: dict[uuid.UUID, NotificationMarker] = {}
    if facts:
        result = await db.execute(
            select(NotificationMarker).where(
                NotificationMarker.user_id == user.id,
                NotificationMarker.dedupe_key.in_([f.dedupe_key for f in facts]),
            )
        )
        markers_by_key = {m.dedupe_key: m for m in result.scalars().all()}

    items: list[NotificationItem] = []
    unread_count = 0
    now = datetime.now(UTC)
    for fact in facts:
        marker = markers_by_key.get(fact.dedupe_key)
        if marker is not None and marker.dismissed_at is not None:
            continue
        is_read = marker is not None and marker.read_at is not None
        if not is_read:
            unread_count += 1
        items.append(
            NotificationItem(
                id=str(fact.dedupe_key),
                source=fact.source,
                title=fact.title,
                body=fact.body,
                action_path=fact.action_path,
                state="read" if is_read else "unread",
                created_at=fact.event_at or (_aware(marker.created_at) if marker else now),
            )
        )
    items.sort(key=lambda i: i.created_at, reverse=True)
    return items, unread_count


async def _upsert_marker(
    db: AsyncSession,
    user: User,
    source: NotificationSource,
    dedupe_key: uuid.UUID,
    *,
    read: bool = False,
    dismissed: bool = False,
) -> None:
    """The only write path in this feature — always an explicit,
    user-initiated action (mark read / dismiss), never a side effect of a
    GET (ArchitectureReview_Phase3.md's read/write discipline)."""
    result = await db.execute(
        select(NotificationMarker).where(
            NotificationMarker.user_id == user.id,
            NotificationMarker.dedupe_key == dedupe_key,
        )
    )
    marker = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if marker is None:
        marker = NotificationMarker(user_id=user.id, source=source, dedupe_key=dedupe_key)
        db.add(marker)
    if read and marker.read_at is None:
        marker.read_at = now
    if dismissed:
        marker.dismissed_at = now
    await db.commit()


async def mark_read(
    db: AsyncSession, user: User, source: NotificationSource, dedupe_key: uuid.UUID
) -> None:
    await _upsert_marker(db, user, source, dedupe_key, read=True)


async def mark_dismissed(
    db: AsyncSession, user: User, source: NotificationSource, dedupe_key: uuid.UUID
) -> None:
    await _upsert_marker(db, user, source, dedupe_key, dismissed=True)
