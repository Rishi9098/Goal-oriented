from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import Dependent, Household, HouseholdMember
from app.models.policy import Scheme
from app.models.user import User
from app.schemas.family_recommendations import (
    FamilyRecommendation,
    RecommendationConflict,
    RecommendationSource,
)
from app.services import family_insurance_service, scheme_eligibility_service
from app.services.planning_service import (
    LOW_SAVINGS_RATE_THRESHOLD,
    FinancialContext,
    _active_goals,
    get_financial_context,
)

# Milestone 2 Task 11 — aggregation only. This module performs zero
# eligibility math and zero deduction-figure computation of its own; every
# why/why_now/used/missing/confidence value is read from an already-
# certified engine (Task 3, Task 10), never recomputed here. See
# RecommendationConflictReview_Task11.md and RecommendationIntegrityReview_
# Task11.md. Recommendation Engine v2 Phase C adds a third source,
# `_financial_health_recommendations`, on the same "read from an
# already-certified engine, never recompute" footing — its engine is
# `planning_service.get_financial_context`, called once by the caller and
# passed in as plain data; this function issues no query of its own.

_INSURANCE_REFERENCE_CODE = "80D"
# Verified fact (GovernmentPolicyReport.md's tax-section table): SSY and
# SCSS both draw from the combined 80C/123 savings-deduction ceiling, not a
# scheme-specific one. Used only to detect a genuine resource conflict if
# the same person ever matched two 80C/123-linked schemes at once — not a
# recommendation priority, a factual grounding reference.
_SAVINGS_SCHEME_REFERENCE_CODE = "80C/123"

# Financial-health rule thresholds (RecommendationEngineV2.md §7 point 2).
# Each is a named, cited constant rather than an inline literal, per this
# codebase's "never invent a financial policy or rate without attribution"
# discipline (Engineering Constitution Rule 2/4) applied to underwriting
# conventions, not just tax law.
_LOW_LIQUIDITY_MONTHS = 3
# A 10% interest rate is the commonly-cited line above which paying down
# debt outperforms most diversified investment portfolios' expected return.
_HIGH_INTEREST_THRESHOLD = 0.10
# 36% is the conventional back-end debt-to-income ceiling used in
# mortgage-underwriting guidelines (not this product's own invention).
_HIGH_DTI_THRESHOLD = 0.36
_STALE_EXPENSE_DAYS = 180


async def _insurance_recommendations(
    db: AsyncSession, user: User, household: Household
) -> list[FamilyRecommendation]:
    rec = await family_insurance_service.compute_insurance_recommendation(db, user, household)
    if rec is None:
        return []
    return [
        FamilyRecommendation(
            source="insurance",
            recommendation_type=rec.recommendation_type,
            subjects=rec.subjects,
            reference_code=_INSURANCE_REFERENCE_CODE,
            why=rec.why,
            why_now=rec.why_now,
            what_information_was_used=rec.what_information_was_used,
            what_information_is_missing=rec.what_information_is_missing,
            confidence_score=rec.confidence_score,
        )
    ]


_WHY_NOW_BY_CATEGORY = {
    "child": (
        "This benefit is tied to {who}'s age — eligibility ends at the scheme's age "
        "ceiling, so starting now maximizes the years it has to compound."
    ),
    "senior": "{who} already meets this scheme's age requirement — there's no reason to wait.",
}


async def _scheme_recommendations(
    db: AsyncSession, household: Household
) -> list[FamilyRecommendation]:
    buckets = await scheme_eligibility_service.evaluate_household_eligibility(db, household.id)
    eligible = buckets.get("eligible", [])
    if not eligible:
        return []

    scheme_codes = {r.scheme_code for r in eligible}
    schemes_result = await db.execute(select(Scheme).where(Scheme.code.in_(scheme_codes)))
    category_by_code = {s.code: s.category for s in schemes_result.scalars().all()}

    members_result = await db.execute(
        select(HouseholdMember, Dependent)
        .join(Dependent, Dependent.household_member_id == HouseholdMember.id)
        .where(HouseholdMember.household_id == household.id, HouseholdMember.is_active.is_(True))
    )
    dependent_by_name = {m.name: d for m, d in members_result.all() if m.name}

    as_of = date.today()
    recommendations: list[FamilyRecommendation] = []
    for result in eligible:
        who = result.member_name or "This household member"
        category = category_by_code.get(result.scheme_code)
        why_now_template = _WHY_NOW_BY_CATEGORY.get(
            category or "", "{who} currently meets this scheme's eligibility criteria."
        )

        what_used = [f"{who}'s eligibility bucket: eligible for {result.scheme_name}"]
        dependent = dependent_by_name.get(result.member_name) if result.member_name else None
        if dependent is not None and dependent.date_of_birth is not None:
            age = scheme_eligibility_service.age_years(dependent.date_of_birth, as_of)
            what_used.append(f"{who}'s date of birth (age {age})")
        if dependent is not None and dependent.gender is not None:
            what_used.append(f"{who}'s recorded gender")

        recommendations.append(
            FamilyRecommendation(
                source="schemes",
                recommendation_type=f"scheme_eligibility:{result.scheme_code}",
                subjects=[result.member_name] if result.member_name else [],
                reference_code=_SAVINGS_SCHEME_REFERENCE_CODE,
                why=result.reason,
                why_now=why_now_template.format(who=who),
                what_information_was_used=what_used,
                what_information_is_missing=[],
                confidence_score=1.0,
            )
        )
    return recommendations


def _aware(dt: datetime) -> datetime:
    """SQLite (this project's test DB) returns naive datetimes even for
    TIMESTAMPTZ columns, unlike Postgres (production) — same quirk, same
    fix, as notification_service.py's own `_aware` helper. Kept as a small,
    separate 2-line function here rather than a shared import: it is too
    small to be worth a cross-module dependency for, per Engineering
    Constitution Rule 7 (no premature abstraction)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _financial_health_recommendations(context: FinancialContext) -> list[FamilyRecommendation]:
    """RecommendationEngineV2.md §6/§7. A pure function over an
    already-computed FinancialContext — no database session, no query, no
    calculation duplicated from get_financial_context or _generate_
    suggestions. `subjects` is always `[]` for every rule here: these are
    account-wide facts, not facts about a named household member, so none
    of these recommendations can ever participate in _detect_conflicts'
    subject-keyed grouping (RecommendationEngineV2.md §7 point 4)."""
    recommendations: list[FamilyRecommendation] = []

    if context.income_source_count == 1:
        recommendations.append(
            FamilyRecommendation(
                source="financial_health",
                recommendation_type="income_concentration",
                subjects=[],
                reference_code="income_concentration",
                why="All of your tracked income comes from a single source.",
                why_now=(
                    "Relying on one income source means a single disruption — a job loss, a "
                    "contract ending — affects all of your recorded income at once."
                ),
                what_information_was_used=["number of active income sources"],
                what_information_is_missing=["any income sources not entered in Financials"],
                confidence_score=1.0,
            )
        )

    if context.expenses_last_updated_at is not None:
        days_stale = (datetime.now(UTC) - _aware(context.expenses_last_updated_at)).days
        if days_stale > _STALE_EXPENSE_DAYS:
            recommendations.append(
                FamilyRecommendation(
                    source="financial_health",
                    recommendation_type="expense_review_prompt",
                    subjects=[],
                    reference_code="expense_review_prompt",
                    why="Your recorded expenses haven't been updated in over 6 months.",
                    why_now=(
                        "They may no longer reflect your actual spending, which affects the "
                        "accuracy of every projection built on top of them."
                    ),
                    what_information_was_used=["most recent expense edit date"],
                    what_information_is_missing=["any spending changes not entered in Financials"],
                    confidence_score=1.0,
                )
            )

    if context.liquid_assets < context.monthly_expenses * _LOW_LIQUIDITY_MONTHS:
        recommendations.append(
            FamilyRecommendation(
                source="financial_health",
                recommendation_type="low_liquidity",
                subjects=[],
                reference_code="low_liquidity",
                why=(
                    f"Your liquid assets cover under {_LOW_LIQUIDITY_MONTHS} months of your "
                    "recorded expenses."
                ),
                why_now=(
                    "A shorter buffer means a smaller unplanned expense could force you to sell "
                    "investments or take on debt."
                ),
                what_information_was_used=["liquid assets", "monthly expenses"],
                what_information_is_missing=["any liquid accounts not entered in Financials"],
                confidence_score=1.0,
            )
        )

    for liability in context.liabilities:
        if (
            liability.interest_rate is not None
            and liability.interest_rate > _HIGH_INTEREST_THRESHOLD
            and liability.balance > 0
        ):
            recommendations.append(
                FamilyRecommendation(
                    source="financial_health",
                    recommendation_type=f"high_interest_debt:{liability.id}",
                    subjects=[],
                    reference_code="high_interest_debt",
                    why=(
                        f"Your {liability.liability_type} carries a "
                        f"{liability.interest_rate * 100:.1f}% interest rate."
                    ),
                    why_now=(
                        "A rate this high usually outperforms most investment returns, so paying "
                        "it down tends to be the higher-value use of extra cash."
                    ),
                    what_information_was_used=[
                        f"{liability.liability_type} interest rate",
                        f"{liability.liability_type} balance",
                    ],
                    what_information_is_missing=[],
                    confidence_score=1.0,
                )
            )

    if 0 < context.savings_rate < LOW_SAVINGS_RATE_THRESHOLD:
        recommendations.append(
            FamilyRecommendation(
                source="financial_health",
                recommendation_type="low_savings_rate",
                subjects=[],
                reference_code="low_savings_rate",
                why=(
                    f"Your savings rate is {context.savings_rate:.0f}% — below the "
                    f"{LOW_SAVINGS_RATE_THRESHOLD:.0f}% target."
                ),
                why_now="Review your monthly expenses to find areas to reduce spending.",
                what_information_was_used=["monthly income", "monthly expenses"],
                what_information_is_missing=[],
                confidence_score=1.0,
            )
        )

    if context.net_worth < 0:
        recommendations.append(
            FamilyRecommendation(
                source="financial_health",
                recommendation_type="negative_net_worth_trend",
                subjects=[],
                reference_code="negative_net_worth_trend",
                why="Your recorded liabilities currently exceed your recorded assets.",
                why_now=(
                    "Tracking this trend over time is the clearest signal of whether your "
                    "overall financial position is improving."
                ),
                what_information_was_used=["total recorded assets", "total recorded liabilities"],
                what_information_is_missing=["any accounts not entered in Financials"],
                confidence_score=1.0,
            )
        )

    if context.debt_ratio > _HIGH_DTI_THRESHOLD:
        recommendations.append(
            FamilyRecommendation(
                source="financial_health",
                recommendation_type="high_debt_to_income",
                subjects=[],
                reference_code="high_debt_to_income",
                why=(
                    f"Your total debt is {context.debt_ratio * 100:.0f}% of your annual income — "
                    f"above the {_HIGH_DTI_THRESHOLD * 100:.0f}% level many lenders treat as a "
                    "risk signal."
                ),
                why_now="This ratio directly affects your ability to qualify for new credit.",
                what_information_was_used=["total recorded liabilities", "total recorded income"],
                what_information_is_missing=["any liabilities or income not entered in Financials"],
                confidence_score=1.0,
            )
        )

    return recommendations


def _detect_conflicts(
    recommendations: list[FamilyRecommendation],
) -> list[RecommendationConflict]:
    """A conflict is two recommendations from different sources sharing a
    subject AND a reference_code — competing for the same bounded
    deduction/scheme ceiling. Never merely 'same person, multiple
    recommendations' (see RecommendationConflictReview_Task11.md). Purely
    additive: nothing is ever removed from `recommendations` as a result."""
    groups: dict[tuple[str, str], set[RecommendationSource]] = {}
    for rec in recommendations:
        for subject in rec.subjects:
            key = (subject, rec.reference_code)
            groups.setdefault(key, set()).add(rec.source)

    conflicts: list[RecommendationConflict] = []
    for (subject, reference_code), sources in groups.items():
        if len(sources) > 1:
            conflicts.append(
                RecommendationConflict(
                    subject=subject,
                    reference_code=reference_code,
                    sources=sorted(sources),
                    note=(
                        f"More than one recommendation for {subject} references the same "
                        f"{reference_code} ceiling — you may not be able to claim the full "
                        f"benefit of both."
                    ),
                )
            )
    return conflicts


async def get_family_recommendations(
    db: AsyncSession, user: User, household: Household
) -> tuple[list[FamilyRecommendation], list[RecommendationConflict]]:
    # `active_goals` is fetched only to satisfy get_financial_context's
    # existing signature (needed to replicate the zero-assets-and-
    # liabilities fallback, ADR-consistent with get_dashboard's own
    # behavior) — reusing planning_service's existing query rather than
    # writing a second one, per "no duplicated calculations."
    active_goals = await _active_goals(db, user.id)
    context = await get_financial_context(db, user, active_goals)

    recommendations = [
        *await _insurance_recommendations(db, user, household),
        *await _scheme_recommendations(db, household),
        *_financial_health_recommendations(context),
    ]
    conflicts = _detect_conflicts(recommendations)
    return recommendations, conflicts
