"""Integration + unit tests for Milestone 2 Task 11 (Family Recommendations):
GET /api/v1/family/recommendations, and the pure conflict-detection helper.

Centered on RecommendationIntegrityReview_Task11.md and
RecommendationConflictReview_Task11.md: every recommendation is fully
explained regardless of source, conflicts are genuine (not "same person,
multiple recommendations"), nothing is persisted, and the Calculation
Lifecycle stays untouched.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.financials import Liability
from app.models.policy import Scheme, SchemeEligibilityRule, TaxAct, TaxSection
from app.schemas.family_recommendations import FamilyRecommendation
from app.services.family_recommendations_service import (
    _detect_conflicts,
    _financial_health_recommendations,
)
from app.services.planning_service import FinancialContext, LOW_SAVINGS_RATE_THRESHOLD


async def _seed_80d_tax_section(db) -> None:
    act = TaxAct(
        name="Income-tax Act, 1961",
        effective_from=date(1962, 4, 1),
        effective_to=date(2026, 3, 31),
    )
    db.add(act)
    await db.flush()
    db.add(
        TaxSection(
            tax_act_id=act.id,
            section_number="80D",
            purpose="health_insurance_premium_deduction",
            limit_amount=25_000.0,
            effective_from=date(1962, 4, 1),
            effective_to=date(2026, 3, 31),
        )
    )
    await db.flush()


async def _seed_ssy_scheme(db) -> None:
    ssy = Scheme(
        code="SSY",
        name="Sukanya Samriddhi Yojana",
        governing_authority="MoF",
        status="active",
        category="child",
    )
    db.add(ssy)
    await db.flush()
    db.add_all(
        [
            SchemeEligibilityRule(
                scheme_id=ssy.id,
                rule_type="max_age",
                operator="lt",
                value="10",
                effective_from=date(2015, 1, 1),
            ),
            SchemeEligibilityRule(
                scheme_id=ssy.id,
                rule_type="gender",
                operator="eq",
                value="female",
                effective_from=date(2015, 1, 1),
            ),
        ]
    )
    await db.flush()


async def _create_parent(
    client: AsyncClient, headers: dict, *, has_own_insurance: str = "no"
) -> str:
    resp = await client.post(
        "/api/v1/family/members",
        json={
            "relationship_type": "parent",
            "name": "Sunita Mehta",
            "relationship_detail": "mother",
            "has_own_insurance": has_own_insurance,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_ssy_eligible_daughter(client: AsyncClient, headers: dict) -> str:
    dob = (date.today() - timedelta(days=365 * 7)).isoformat()
    resp = await client.post(
        "/api/v1/family/members",
        json={
            "relationship_type": "child",
            "name": "Ananya Mehta",
            "date_of_birth": dob,
            "gender": "female",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
class TestFamilyRecommendationsEndpoint:
    async def test_empty_household_has_no_recommendations(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/api/v1/family/recommendations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["recommendations"] == []
        assert resp.json()["conflicts"] == []

    async def test_insurance_only_recommendation(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        await _seed_80d_tax_section(db)
        await _create_parent(client, auth_headers, has_own_insurance="no")
        resp = await client.get("/api/v1/family/recommendations", headers=auth_headers)
        recs = resp.json()["recommendations"]
        assert len(recs) == 1
        assert recs[0]["source"] == "insurance"

    async def test_schemes_only_recommendation(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        await _seed_ssy_scheme(db)
        await _create_ssy_eligible_daughter(client, auth_headers)
        resp = await client.get("/api/v1/family/recommendations", headers=auth_headers)
        recs = resp.json()["recommendations"]
        assert len(recs) == 1
        assert recs[0]["source"] == "schemes"
        assert recs[0]["reference_code"] == "80C/123"

    async def test_both_sources_present_no_false_conflict(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        """Insurance (80D) and schemes (80C/123) about different people
        must never be flagged as conflicting — different reference codes,
        different subjects."""
        await _seed_80d_tax_section(db)
        await _seed_ssy_scheme(db)
        await _create_parent(client, auth_headers, has_own_insurance="no")
        await _create_ssy_eligible_daughter(client, auth_headers)

        resp = await client.get("/api/v1/family/recommendations", headers=auth_headers)
        data = resp.json()
        sources = {r["source"] for r in data["recommendations"]}
        assert sources == {"insurance", "schemes"}
        assert data["conflicts"] == []

    async def test_every_recommendation_fully_explained(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        await _seed_80d_tax_section(db)
        await _seed_ssy_scheme(db)
        await _create_parent(client, auth_headers, has_own_insurance="no")
        await _create_ssy_eligible_daughter(client, auth_headers)

        resp = await client.get("/api/v1/family/recommendations", headers=auth_headers)
        for rec in resp.json()["recommendations"]:
            assert rec["why"]
            assert rec["why_now"]
            assert isinstance(rec["what_information_was_used"], list)
            assert len(rec["what_information_was_used"]) > 0
            assert isinstance(rec["what_information_is_missing"], list)
            assert 0 <= rec["confidence_score"] <= 1

    async def test_scheme_recommendation_confidence_is_full(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        """Eligibility is a deterministic rule match — confidence is always
        1.0, never an invented lower number for a case that isn't actually
        uncertain."""
        await _seed_ssy_scheme(db)
        await _create_ssy_eligible_daughter(client, auth_headers)
        resp = await client.get("/api/v1/family/recommendations", headers=auth_headers)
        assert resp.json()["recommendations"][0]["confidence_score"] == 1.0

    async def test_nothing_is_persisted(self, client: AsyncClient, auth_headers: dict, db):
        from sqlalchemy import select

        from app.models.recommendation import Recommendation

        await _seed_80d_tax_section(db)
        await _create_parent(client, auth_headers, has_own_insurance="no")
        await client.get("/api/v1/family/recommendations", headers=auth_headers)

        result = await db.execute(select(Recommendation))
        assert result.scalars().all() == []

    async def test_calculation_lifecycle_untouched(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        await _seed_80d_tax_section(db)
        goal_resp = await client.post(
            "/api/v1/goals",
            json={
                "name": "Emergency Fund",
                "category": "emergency",
                "target_amount": 50_000,
                "current_amount": 10_000,
                "target_date": "2030-01-01",
                "monthly_contribution": 500,
                "risk_profile": "balanced",
            },
            headers=auth_headers,
        )
        original_probability = goal_resp.json()["probability"]

        await _create_parent(client, auth_headers, has_own_insurance="no")
        await client.get("/api/v1/family/recommendations", headers=auth_headers)

        get_goal = await client.get(
            f"/api/v1/goals/{goal_resp.json()['id']}", headers=auth_headers
        )
        assert get_goal.json()["probability"] == original_probability

    async def test_recommendations_isolated_between_users(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict, db
    ):
        await _seed_80d_tax_section(db)
        await _create_parent(client, other_auth_headers, has_own_insurance="no")
        resp = await client.get("/api/v1/family/recommendations", headers=auth_headers)
        assert resp.json()["recommendations"] == []


class TestConflictDetection:
    """Unit tests against the pure helper directly — the real seeded
    schemes never produce a genuine conflict (SSY=child, SCSS=senior can't
    both match one person), so this exercises the mechanism in isolation
    per RecommendationConflictReview_Task11.md."""

    def _rec(self, source: str, subjects: list[str], reference_code: str) -> FamilyRecommendation:
        return FamilyRecommendation(
            source=source,
            recommendation_type="test",
            subjects=subjects,
            reference_code=reference_code,
            why="why",
            why_now="why_now",
            what_information_was_used=["used"],
            what_information_is_missing=[],
            confidence_score=1.0,
        )

    def test_same_subject_different_reference_code_no_conflict(self):
        recs = [
            self._rec("insurance", ["Sunita"], "80D"),
            self._rec("schemes", ["Sunita"], "80C/123"),
        ]
        assert _detect_conflicts(recs) == []

    def test_different_subject_same_reference_code_no_conflict(self):
        recs = [
            self._rec("schemes", ["Ananya"], "80C/123"),
            self._rec("schemes", ["Ravi"], "80C/123"),
        ]
        assert _detect_conflicts(recs) == []

    def test_same_subject_same_reference_code_different_sources_is_a_conflict(self):
        recs = [
            self._rec("insurance", ["Sunita"], "80D"),
            self._rec("schemes", ["Sunita"], "80D"),
        ]
        conflicts = _detect_conflicts(recs)
        assert len(conflicts) == 1
        assert conflicts[0].subject == "Sunita"
        assert set(conflicts[0].sources) == {"insurance", "schemes"}

    def test_conflict_never_removes_a_recommendation(self):
        """Conflicts are additive metadata only — never a suppression
        mechanism (do not hardcode recommendation priorities)."""
        recs = [
            self._rec("insurance", ["Sunita"], "80D"),
            self._rec("schemes", ["Sunita"], "80D"),
        ]
        conflicts = _detect_conflicts(recs)
        assert len(conflicts) == 1
        assert len(recs) == 2


def _make_liability(**kwargs: object) -> Liability:
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        liability_type="mortgage",
        institution=None,
        description=None,
        balance=100_000.0,
        interest_rate=None,
        monthly_payment=0.0,
        is_active=True,
    )
    defaults.update(kwargs)
    return Liability(**defaults)


def _context(**overrides: object) -> FinancialContext:
    """A neutral, non-triggering FinancialContext by default — every
    financial-health test overrides only the one or two fields its own
    rule cares about, so a passing test proves that field, and nothing
    else, controls the outcome."""
    defaults: dict[str, object] = dict(
        monthly_income=10_000.0,
        monthly_expenses=3_000.0,
        monthly_savings=7_000.0,
        savings_rate=70.0,
        net_worth=50_000.0,
        liquid_assets=50_000.0,
        invested_assets=0.0,
        total_assets=50_000.0,
        total_liabilities=0.0,
        debt_ratio=0.0,
        liabilities=[],
        expenses_last_updated_at=None,
        income_source_count=2,
    )
    defaults.update(overrides)
    return FinancialContext(**defaults)  # type: ignore[arg-type]


class TestFinancialHealthRecommendations:
    """Recommendation Engine v2, Phase C (RecommendationEngineV2.md §6) —
    pure unit tests against `_financial_health_recommendations` directly,
    no database, matching TestConflictDetection's existing style. Every
    rule gets a firing case and a non-firing case."""

    def _types(self, context: FinancialContext) -> set[str]:
        return {
            r.recommendation_type.split(":")[0]
            for r in _financial_health_recommendations(context)
        }

    def test_income_concentration_fires_at_exactly_one_source(self):
        assert "income_concentration" in self._types(_context(income_source_count=1))

    def test_income_concentration_does_not_fire_with_two_sources(self):
        assert "income_concentration" not in self._types(_context(income_source_count=2))

    def test_income_concentration_does_not_fire_with_zero_sources(self):
        assert "income_concentration" not in self._types(_context(income_source_count=0))

    def test_expense_review_prompt_fires_when_stale(self):
        stale = datetime.now(UTC) - timedelta(days=200)
        assert "expense_review_prompt" in self._types(
            _context(expenses_last_updated_at=stale)
        )

    def test_expense_review_prompt_does_not_fire_when_recent(self):
        recent = datetime.now(UTC) - timedelta(days=10)
        assert "expense_review_prompt" not in self._types(
            _context(expenses_last_updated_at=recent)
        )

    def test_expense_review_prompt_does_not_fire_with_no_expenses(self):
        assert "expense_review_prompt" not in self._types(
            _context(expenses_last_updated_at=None)
        )

    def test_low_liquidity_fires_below_three_months_expenses(self):
        context = _context(monthly_expenses=3_000.0, liquid_assets=5_000.0)
        assert "low_liquidity" in self._types(context)

    def test_low_liquidity_does_not_fire_at_three_months_or_more(self):
        context = _context(monthly_expenses=3_000.0, liquid_assets=9_000.0)
        assert "low_liquidity" not in self._types(context)

    def test_high_interest_debt_fires_per_qualifying_liability(self):
        high = _make_liability(liability_type="credit_card", interest_rate=0.22, balance=5_000.0)
        low = _make_liability(liability_type="mortgage", interest_rate=0.06, balance=280_000.0)
        recs = _financial_health_recommendations(_context(liabilities=[high, low]))
        matching = [r for r in recs if r.recommendation_type.startswith("high_interest_debt:")]
        assert len(matching) == 1
        assert str(high.id) in matching[0].recommendation_type

    def test_high_interest_debt_does_not_fire_below_threshold(self):
        low = _make_liability(interest_rate=0.06, balance=280_000.0)
        assert "high_interest_debt" not in self._types(_context(liabilities=[low]))

    def test_high_interest_debt_ignores_liability_with_no_interest_rate(self):
        unset = _make_liability(interest_rate=None, balance=5_000.0)
        assert "high_interest_debt" not in self._types(_context(liabilities=[unset]))

    def test_low_savings_rate_fires_below_threshold(self):
        below = LOW_SAVINGS_RATE_THRESHOLD - 1
        assert "low_savings_rate" in self._types(_context(savings_rate=below))

    def test_low_savings_rate_does_not_fire_at_or_above_threshold(self):
        assert "low_savings_rate" not in self._types(
            _context(savings_rate=LOW_SAVINGS_RATE_THRESHOLD)
        )

    def test_low_savings_rate_does_not_fire_at_exactly_zero(self):
        """Matches _generate_suggestions' own `0 < savings_rate` guard —
        a savings rate of exactly 0 (no income at all) is a different
        problem than 'below target', and must not double-report as both."""
        assert "low_savings_rate" not in self._types(_context(savings_rate=0.0))

    def test_negative_net_worth_fires_when_negative(self):
        assert "negative_net_worth_trend" in self._types(_context(net_worth=-1.0))

    def test_negative_net_worth_does_not_fire_at_zero_or_positive(self):
        assert "negative_net_worth_trend" not in self._types(_context(net_worth=0.0))
        assert "negative_net_worth_trend" not in self._types(_context(net_worth=1.0))

    def test_high_debt_to_income_fires_above_threshold(self):
        assert "high_debt_to_income" in self._types(_context(debt_ratio=0.37))

    def test_high_debt_to_income_does_not_fire_at_or_below_threshold(self):
        assert "high_debt_to_income" not in self._types(_context(debt_ratio=0.36))

    def test_neutral_context_produces_no_recommendations(self):
        assert _financial_health_recommendations(_context()) == []

    def test_every_financial_health_recommendation_uses_the_correct_source_and_no_subjects(self):
        context = _context(income_source_count=1, net_worth=-1.0)
        recs = _financial_health_recommendations(context)
        assert len(recs) >= 2
        for rec in recs:
            assert rec.source == "financial_health"
            assert rec.subjects == []
            assert rec.confidence_score == 1.0
            assert rec.why
            assert rec.why_now

    def test_financial_health_recommendations_never_participate_in_conflicts(self):
        """subjects=[] structurally excludes every financial-health
        recommendation from _detect_conflicts' subject-keyed grouping
        (RecommendationEngineV2.md §7 point 4) — proven, not assumed, even
        against a coincidentally-matching reference_code from another
        source."""
        financial = _financial_health_recommendations(_context(net_worth=-1.0))
        other_source = FamilyRecommendation(
            source="insurance",
            recommendation_type="test",
            subjects=["Someone"],
            reference_code="negative_net_worth_trend",  # deliberately coincidental
            why="why",
            why_now="why_now",
            what_information_was_used=["used"],
            what_information_is_missing=[],
            confidence_score=1.0,
        )
        conflicts = _detect_conflicts([*financial, other_source])
        assert conflicts == []


@pytest.mark.asyncio
class TestFinancialHealthRecommendationsEndToEnd:
    """Integration tests via the real endpoints — proves each of the four
    financial-facts entities, when edited through the same PATCH endpoints
    Milestone 1 Tasks 3-6 built, changes what `/family/recommendations`
    returns. No mocking, no direct FinancialContext construction — this is
    the literal 'Income change → Recommendation changes' etc. requirement,
    exercised end to end."""

    async def _recommendation_types(self, client: AsyncClient, headers: dict) -> set[str]:
        resp = await client.get("/api/v1/family/recommendations", headers=headers)
        assert resp.status_code == 200
        return {
            r["recommendation_type"].split(":")[0] for r in resp.json()["recommendations"]
        }

    async def test_income_change_triggers_income_concentration_recommendation(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        create = await client.post(
            "/api/v1/financials/income",
            json={"source_type": "salary", "annual_amount": 120_000},
            headers=auth_headers,
        )
        assert create.status_code == 201

        assert "income_concentration" in await self._recommendation_types(client, auth_headers)

        # Adding a second income source removes the concentration signal —
        # the recommendation set must change as a direct result.
        await client.post(
            "/api/v1/financials/income",
            json={"source_type": "freelance", "annual_amount": 20_000},
            headers=auth_headers,
        )
        assert "income_concentration" not in await self._recommendation_types(
            client, auth_headers
        )

    async def test_expense_change_triggers_low_savings_rate_recommendation(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post(
            "/api/v1/financials/income",
            json={"source_type": "salary", "annual_amount": 120_000},
            headers=auth_headers,
        )
        expense = await client.post(
            "/api/v1/financials/expenses",
            json={"category": "housing", "monthly_amount": 500},
            headers=auth_headers,
        )
        assert expense.status_code == 201
        expense_id = expense.json()["id"]

        # $500/mo against $10,000/mo income is a 95% savings rate — no
        # low_savings_rate recommendation yet.
        assert "low_savings_rate" not in await self._recommendation_types(client, auth_headers)

        # Raising the expense to $8,700/mo drops the savings rate to 13%,
        # below the 15% threshold — the recommendation must now appear.
        patch = await client.patch(
            f"/api/v1/financials/expenses/{expense_id}",
            json={"monthly_amount": 8_700},
            headers=auth_headers,
        )
        assert patch.status_code == 200
        assert "low_savings_rate" in await self._recommendation_types(client, auth_headers)

    async def test_asset_change_triggers_low_liquidity_recommendation(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post(
            "/api/v1/financials/expenses",
            json={"category": "housing", "monthly_amount": 3_000},
            headers=auth_headers,
        )
        asset = await client.post(
            "/api/v1/financials/assets",
            json={"asset_type": "savings", "current_value": 2_000},
            headers=auth_headers,
        )
        assert asset.status_code == 201
        asset_id = asset.json()["id"]

        # $2,000 liquid against $3,000/mo expenses is under 3 months' cover.
        assert "low_liquidity" in await self._recommendation_types(client, auth_headers)

        # Raising the balance to $10,000 clears the 3-month threshold —
        # the recommendation must disappear as a direct result.
        patch = await client.patch(
            f"/api/v1/financials/assets/{asset_id}",
            json={"current_value": 10_000},
            headers=auth_headers,
        )
        assert patch.status_code == 200
        assert "low_liquidity" not in await self._recommendation_types(client, auth_headers)

    async def test_liability_change_triggers_high_interest_debt_recommendation(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        liability = await client.post(
            "/api/v1/financials/liabilities",
            json={
                "liability_type": "credit_card",
                "balance": 5_000,
                "interest_rate": 0.22,
                "monthly_payment": 200,
            },
            headers=auth_headers,
        )
        assert liability.status_code == 201
        liability_id = liability.json()["id"]

        # 22% interest is above the 10% high-interest threshold.
        assert "high_interest_debt" in await self._recommendation_types(client, auth_headers)

        # Paying the rate down to 5% (e.g. a balance transfer) removes the
        # recommendation — the recommendation set changes as a direct
        # result of the liability edit, not a coincidence of timing.
        patch = await client.patch(
            f"/api/v1/financials/liabilities/{liability_id}",
            json={"interest_rate": 0.05},
            headers=auth_headers,
        )
        assert patch.status_code == 200
        assert "high_interest_debt" not in await self._recommendation_types(
            client, auth_headers
        )
