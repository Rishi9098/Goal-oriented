"""Government scheme eligibility evaluation — Milestone 2 Task 3.

Deliberately narrow: evaluates exactly the rule_types this codebase has
verified, seeded data for (max_age, min_age, gender), not a general rule
interpreter. Extending to a fourth rule_type is a decision to make when a
scheme actually needs one (docs/ENGINEERING_CONSTITUTION.md Rule 7), not
ahead of need.

Consumed by two places, both reusing this single evaluation path so
eligibility logic is never duplicated (docs/ENGINEERING_CONSTITUTION.md):
the Add-Child inline SSY callout (family_service.create_member/update_member)
and the Family Government Schemes screen (Task 11, not yet built).

Known, deliberate limitations (see DesignReview.md / seed_policy_data.py):
- Evaluates non-`self` household members only (spouse/child/parent/other —
  the ones with a `Dependent` row). A `self` member's own age lives on
  `UserProfile`, a different join this task's two illustrative use cases
  (child SSY, parent/senior SCSS) don't require; a documented future
  extension, not a bug.
- SCSS's 55+ (VRS retiree) / 50+ (defense personnel) special-case routes
  are not evaluated — no seeded rule exists for them, since this app
  captures no retirement/defense-service field to check them against.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import Dependent, HouseholdMember
from app.models.policy import Scheme, SchemeEligibilityRule

EligibilityBucket = Literal["eligible", "potentially_eligible", "not_eligible"]

# A minimum-age rule not yet met is "potentially eligible" rather than "not
# eligible" if the member is within this many years of the threshold — a
# product decision (DesignReview.md), not a financial/policy fact. Does not
# apply to maximum-age ceilings (SSY): once a child ages out, there is no
# "potentially eligible by getting older" direction.
_POTENTIALLY_ELIGIBLE_WINDOW_YEARS = 5


@dataclass(frozen=True)
class EligibilityResult:
    scheme_code: str
    scheme_name: str
    bucket: EligibilityBucket
    member_name: str | None
    reason: str


def age_years(dob: date, as_of: date) -> int:
    """Exact completed-years age (the standard calendar idiom), not a
    days/365.25 approximation — the latter can drift across an exact
    threshold (e.g. a child's precise 10th birthday) depending on how many
    leap days happen to fall within the specific span being measured, which
    would be a real correctness bug at exactly the boundary this function
    exists to get right. Public (Milestone 2 Task 10): reused by
    family_insurance_service for senior-citizen (60+) determination — pure
    date arithmetic, not scheme-evaluation logic, so reusing it does not
    blur the schemes/insurance boundary (see RecommendationIntegrityReview_
    Task10.md #5)."""
    return as_of.year - dob.year - ((as_of.month, as_of.day) < (dob.month, dob.day))


def _evaluate_rules_for_member(
    scheme: Scheme,
    rules: list[SchemeEligibilityRule],
    member_name: str | None,
    dependent: Dependent,
    as_of: date,
) -> tuple[EligibilityBucket, str] | None:
    """None means "cannot evaluate yet" (e.g. an incomplete placeholder
    member with no date_of_birth) — the caller skips this member for this
    scheme rather than guessing."""
    approaching_min_age = False

    for rule in rules:
        if rule.rule_type == "max_age" and rule.operator == "lt":
            if dependent.date_of_birth is None:
                return None
            age = age_years(dependent.date_of_birth, as_of)
            threshold = float(rule.value)
            if age >= threshold:
                return "not_eligible", (
                    f"{member_name or 'This household member'} is over the age limit "
                    f"for {scheme.name} (must be under {int(threshold)})."
                )

        elif rule.rule_type == "min_age" and rule.operator == "gte":
            if dependent.date_of_birth is None:
                return None
            age = age_years(dependent.date_of_birth, as_of)
            threshold = float(rule.value)
            if age < threshold:
                years_remaining = threshold - age
                if years_remaining <= _POTENTIALLY_ELIGIBLE_WINDOW_YEARS:
                    approaching_min_age = True
                else:
                    return "not_eligible", (
                        f"{member_name or 'This household member'} does not yet meet "
                        f"the age {int(threshold)}+ requirement for {scheme.name}."
                    )

        elif rule.rule_type == "gender" and rule.operator == "eq":
            if dependent.gender != rule.value:
                return "not_eligible", (
                    f"{scheme.name} has a gender-specific eligibility requirement "
                    f"that {member_name or 'this household member'} does not meet."
                )
        # Other rule_types (e.g. residency_status): no seeded rows yet, so no
        # branch — an unrecognized rule_type is silently not evaluated
        # rather than guessed at, consistent with this module's narrow scope.

    if approaching_min_age:
        min_age_rule = next(
            r for r in rules if r.rule_type == "min_age" and r.operator == "gte"
        )
        threshold_int = int(float(min_age_rule.value))
        return "potentially_eligible", (
            f"{member_name or 'This household member'} will reach the age "
            f"{threshold_int}+ requirement for {scheme.name} within the next "
            f"{int(_POTENTIALLY_ELIGIBLE_WINDOW_YEARS)} years."
        )

    who = member_name or "This household member"
    return "eligible", f"{who} meets the current criteria for {scheme.name}."


async def evaluate_household_eligibility(
    db: AsyncSession, household_id: uuid.UUID, as_of: date | None = None
) -> dict[EligibilityBucket, list[EligibilityResult]]:
    as_of = as_of or date.today()

    schemes = list((await db.execute(select(Scheme))).scalars().all())

    rules_by_scheme: dict[uuid.UUID, list[SchemeEligibilityRule]] = {}
    for rule in (await db.execute(select(SchemeEligibilityRule))).scalars().all():
        rules_by_scheme.setdefault(rule.scheme_id, []).append(rule)

    members_result = await db.execute(
        select(HouseholdMember, Dependent)
        .join(Dependent, Dependent.household_member_id == HouseholdMember.id)
        .where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.is_active.is_(True),
            HouseholdMember.relationship_type != "self",
        )
    )
    members = list(members_result.all())

    buckets: dict[EligibilityBucket, list[EligibilityResult]] = {
        "eligible": [],
        "potentially_eligible": [],
        "not_eligible": [],
    }

    for scheme in schemes:
        if scheme.status == "closed_to_new":
            buckets["not_eligible"].append(
                EligibilityResult(
                    scheme_code=scheme.code,
                    scheme_name=scheme.name,
                    bucket="not_eligible",
                    member_name=None,
                    reason=f"{scheme.name} is closed to new subscriptions.",
                )
            )
            continue

        rules = rules_by_scheme.get(scheme.id, [])
        if not rules:
            # No seeded eligibility rules for this scheme yet — cannot
            # evaluate, so it stays out of eligible/potentially_eligible
            # rather than being guessed into either.
            buckets["not_eligible"].append(
                EligibilityResult(
                    scheme_code=scheme.code,
                    scheme_name=scheme.name,
                    bucket="not_eligible",
                    member_name=None,
                    reason=f"Eligibility criteria for {scheme.name} are not yet configured.",
                )
            )
            continue

        any_match_for_scheme = False
        for member, dependent in members:
            outcome = _evaluate_rules_for_member(
                scheme, rules, member.name, dependent, as_of
            )
            if outcome is None:
                continue
            bucket, reason = outcome
            if bucket in ("eligible", "potentially_eligible"):
                any_match_for_scheme = True
            buckets[bucket].append(
                EligibilityResult(
                    scheme_code=scheme.code,
                    scheme_name=scheme.name,
                    bucket=bucket,
                    member_name=member.name,
                    reason=reason,
                )
            )

        if not any_match_for_scheme and not members:
            buckets["not_eligible"].append(
                EligibilityResult(
                    scheme_code=scheme.code,
                    scheme_name=scheme.name,
                    bucket="not_eligible",
                    member_name=None,
                    reason=(
                        f"No household member currently matches {scheme.name}'s "
                        "eligibility criteria."
                    ),
                )
            )

    return buckets


async def check_ssy_eligibility(
    db: AsyncSession, member_name: str | None, dependent: Dependent, as_of: date | None = None
) -> EligibilityResult | None:
    """Narrow helper for the Add-Child inline callout (family_service) —
    checks a single child against SSY only, reusing the same rule-evaluation
    function as the full household evaluation above rather than duplicating
    the age/gender logic. Returns None if not eligible or not evaluable
    (never returns a 'not_eligible' result here — the inline callout only
    ever shows a positive match, per FamilyPlanningDesign.md Part 4.2)."""
    as_of = as_of or date.today()
    scheme = (
        await db.execute(select(Scheme).where(Scheme.code == "SSY"))
    ).scalar_one_or_none()
    if scheme is None:
        return None

    rules = list(
        (
            await db.execute(
                select(SchemeEligibilityRule).where(SchemeEligibilityRule.scheme_id == scheme.id)
            )
        )
        .scalars()
        .all()
    )
    if not rules:
        return None

    outcome = _evaluate_rules_for_member(scheme, rules, member_name, dependent, as_of)
    if outcome is None or outcome[0] != "eligible":
        return None
    return EligibilityResult(
        scheme_code=scheme.code,
        scheme_name=scheme.name,
        bucket="eligible",
        member_name=member_name,
        reason=outcome[1],
    )
