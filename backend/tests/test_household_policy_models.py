"""Model-level tests for Milestone 1's foundation tables: household/family,
government policy engine, estate/nominee, insurance, recommendation, and
audit. These are new tables with no routers yet, so tests exercise the
SQLAlchemy models directly via the `db` session fixture rather than through
the HTTP client, matching how a schema-only milestone should be validated.
"""

from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.estate import EstateDocument, HUFCoparcener, HUFEntity, Nominee
from app.models.financials import Asset
from app.models.household import Dependent, Household, HouseholdMember
from app.models.insurance import HealthPolicy, HealthPolicyCoverage
from app.models.policy import (
    Scheme,
    SchemeEligibilityRule,
    SchemeRate,
    TaxAct,
    TaxRegime,
    TaxSection,
    TaxSlab,
)
from app.models.recommendation import Recommendation, RecommendationCitation
from app.models.user import User


@pytest.mark.asyncio
class TestHouseholdModels:
    async def test_household_with_login_and_no_login_members(
        self, db: AsyncSession, user: User
    ) -> None:
        # Arrange
        household = Household(name="The Sharma Family", created_by_user_id=user.id)
        db.add(household)
        await db.flush()

        adult_member = HouseholdMember(
            household_id=household.id, user_id=user.id, relationship_type="self"
        )
        # A dependent daughter has no login of her own — user_id must be
        # nullable, per FamilyHUFPlanningReport.md's SSY scenario.
        child_member = HouseholdMember(
            household_id=household.id, user_id=None, relationship_type="child"
        )
        db.add_all([adult_member, child_member])
        await db.flush()

        dependent = Dependent(
            household_member_id=child_member.id,
            date_of_birth=date(2020, 1, 1),
            dependent_type="minor_child",
            is_tax_dependent=True,
        )
        db.add(dependent)
        await db.flush()

        # Act
        result = await db.execute(
            select(HouseholdMember).where(HouseholdMember.household_id == household.id)
        )
        members = result.scalars().all()

        # Assert
        assert len(members) == 2
        assert any(m.user_id is None for m in members)
        assert any(m.user_id == user.id for m in members)

    async def test_deleting_household_cascades_to_members(
        self, db: AsyncSession, user: User
    ) -> None:
        household = Household(name="Test Household", created_by_user_id=user.id)
        db.add(household)
        await db.flush()
        member = HouseholdMember(
            household_id=household.id, user_id=user.id, relationship_type="self"
        )
        db.add(member)
        await db.flush()
        member_id = member.id

        await db.delete(household)
        await db.flush()

        result = await db.execute(
            select(HouseholdMember).where(HouseholdMember.id == member_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
class TestPolicyEngineModels:
    async def test_scheme_with_versioned_rate_and_eligibility_rule(self, db: AsyncSession) -> None:
        scheme = Scheme(
            code="PPF",
            name="Public Provident Fund",
            governing_authority="Ministry of Finance / RBI",
            status="active",
            category="general_savings",
        )
        db.add(scheme)
        await db.flush()

        rate = SchemeRate(
            scheme_id=scheme.id,
            field_name="interest_rate",
            value=7.1,
            effective_from=date(2026, 4, 1),
            source_citation="ClearTax PPF — verified 2026-07-06",
        )
        rule = SchemeEligibilityRule(
            scheme_id=scheme.id,
            rule_type="residency_status",
            operator="eq",
            value="resident",
            effective_from=date(2026, 4, 1),
        )
        db.add_all([rate, rule])
        await db.flush()

        result = await db.execute(select(SchemeRate).where(SchemeRate.scheme_id == scheme.id))
        assert result.scalar_one().value == pytest.approx(7.1)

    async def test_closed_to_new_scheme_status_persists(self, db: AsyncSession) -> None:
        # PMVVY-shaped case: a scheme closed to new subscribers must retain
        # that status distinctly from "active" — see GovernmentPolicyReport.md.
        scheme = Scheme(
            code="PMVVY",
            name="Pradhan Mantri Vaya Vandana Yojana",
            governing_authority="LIC / Ministry of Finance",
            status="closed_to_new",
            category="senior",
        )
        db.add(scheme)
        await db.flush()

        result = await db.execute(select(Scheme).where(Scheme.code == "PMVVY"))
        assert result.scalar_one().status == "closed_to_new"

    async def test_tax_act_section_renumbering_both_versions_queryable(
        self, db: AsyncSession
    ) -> None:
        # The single most important finding in GovernmentPolicyReport.md:
        # Section 80C (1961 Act) becomes Section 123 (2025 Act) for the same
        # deduction. Both must be independently queryable by effective date.
        old_act = TaxAct(
            name="Income-tax Act, 1961",
            effective_from=date(1962, 4, 1),
            effective_to=date(2026, 3, 31),
        )
        new_act = TaxAct(name="Income-tax Act, 2025", effective_from=date(2026, 4, 1))
        db.add_all([old_act, new_act])
        await db.flush()

        db.add_all(
            [
                TaxSection(
                    tax_act_id=old_act.id,
                    section_number="80C",
                    purpose="general_savings_deduction",
                    limit_amount=150_000.0,
                    effective_from=date(1962, 4, 1),
                    effective_to=date(2026, 3, 31),
                ),
                TaxSection(
                    tax_act_id=new_act.id,
                    section_number="123",
                    purpose="general_savings_deduction",
                    limit_amount=150_000.0,
                    effective_from=date(2026, 4, 1),
                ),
            ]
        )
        await db.flush()

        result = await db.execute(
            select(TaxSection).where(TaxSection.purpose == "general_savings_deduction")
        )
        sections = result.scalars().all()
        assert {s.section_number for s in sections} == {"80C", "123"}
        assert all(s.limit_amount == pytest.approx(150_000.0) for s in sections)

    async def test_tax_regime_slabs(self, db: AsyncSession) -> None:
        regime = TaxRegime(name="new", effective_from=date(2026, 4, 1))
        db.add(regime)
        await db.flush()
        db.add_all(
            [
                TaxSlab(
                    tax_regime_id=regime.id,
                    income_from=0.0,
                    income_to=400_000.0,
                    rate_percent=0.0,
                    effective_from=date(2026, 4, 1),
                ),
                TaxSlab(
                    tax_regime_id=regime.id,
                    income_from=2_400_000.0,
                    income_to=None,  # no upper bound on the top slab
                    rate_percent=30.0,
                    effective_from=date(2026, 4, 1),
                ),
            ]
        )
        await db.flush()

        result = await db.execute(select(TaxSlab).where(TaxSlab.tax_regime_id == regime.id))
        slabs = result.scalars().all()
        assert len(slabs) == 2
        assert any(s.income_to is None for s in slabs)


@pytest.mark.asyncio
class TestEstateAndNomineeModels:
    async def test_huf_requires_funding_source(self, db: AsyncSession, user: User) -> None:
        huf = HUFEntity(
            karta_user_id=user.id,
            funding_source="ancestral_property",
            formation_date=date(2020, 1, 1),
        )
        db.add(huf)
        await db.flush()

        household = Household(name="HUF Household", created_by_user_id=user.id)
        db.add(household)
        await db.flush()
        member = HouseholdMember(
            household_id=household.id, user_id=user.id, relationship_type="self"
        )
        db.add(member)
        await db.flush()

        coparcener = HUFCoparcener(huf_entity_id=huf.id, household_member_id=member.id)
        db.add(coparcener)
        await db.flush()

        result = await db.execute(
            select(HUFEntity).where(HUFEntity.karta_user_id == user.id)
        )
        assert result.scalar_one().funding_source == "ancestral_property"

    async def test_nominee_percentage_share_within_valid_range(
        self, db: AsyncSession, user: User
    ) -> None:
        asset = Asset(user_id=user.id, asset_type="brokerage", current_value=100_000.0)
        db.add(asset)
        await db.flush()

        nominee = Nominee(
            asset_id=asset.id,
            name="Jane Doe",
            relationship_type="spouse",
            percentage_share=100.0,
        )
        db.add(nominee)
        await db.flush()

        result = await db.execute(select(Nominee).where(Nominee.asset_id == asset.id))
        assert result.scalar_one().percentage_share == pytest.approx(100.0)

    async def test_nominee_percentage_share_over_100_rejected(
        self, db: AsyncSession, user: User
    ) -> None:
        asset = Asset(user_id=user.id, asset_type="brokerage", current_value=100_000.0)
        db.add(asset)
        await db.flush()

        db.add(
            Nominee(
                asset_id=asset.id,
                name="Jane Doe",
                relationship_type="spouse",
                percentage_share=150.0,
            )
        )
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_nominee_percentage_share_zero_rejected(
        self, db: AsyncSession, user: User
    ) -> None:
        asset = Asset(user_id=user.id, asset_type="brokerage", current_value=100_000.0)
        db.add(asset)
        await db.flush()

        db.add(
            Nominee(
                asset_id=asset.id,
                name="Jane Doe",
                relationship_type="spouse",
                percentage_share=0.0,
            )
        )
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_estate_document_stores_status_only(self, db: AsyncSession, user: User) -> None:
        doc = EstateDocument(user_id=user.id, document_type="will", status="drafted")
        db.add(doc)
        await db.flush()

        result = await db.execute(select(EstateDocument).where(EstateDocument.user_id == user.id))
        stored = result.scalar_one()
        assert stored.status == "drafted"
        assert not hasattr(stored, "content")


@pytest.mark.asyncio
class TestInsuranceModels:
    async def test_family_floater_covers_multiple_household_members(
        self, db: AsyncSession, user: User
    ) -> None:
        household = Household(name="Insurance Household", created_by_user_id=user.id)
        db.add(household)
        await db.flush()
        member = HouseholdMember(
            household_id=household.id, user_id=user.id, relationship_type="self"
        )
        db.add(member)
        await db.flush()

        policy = HealthPolicy(
            primary_holder_user_id=user.id,
            policy_type="family_floater",
            sum_insured=1_500_000.0,
            annual_premium=25_000.0,
        )
        db.add(policy)
        await db.flush()

        coverage = HealthPolicyCoverage(health_policy_id=policy.id, household_member_id=member.id)
        db.add(coverage)
        await db.flush()

        result = await db.execute(
            select(HealthPolicyCoverage).where(HealthPolicyCoverage.health_policy_id == policy.id)
        )
        assert result.scalar_one().household_member_id == member.id


@pytest.mark.asyncio
class TestRecommendationAndAuditModels:
    async def test_recommendation_with_citation_and_structured_fields(
        self, db: AsyncSession, user: User
    ) -> None:
        scheme = Scheme(
            code="NPS",
            name="National Pension System",
            governing_authority="PFRDA",
            status="active",
            category="retirement",
        )
        db.add(scheme)
        await db.flush()

        recommendation = Recommendation(
            user_id=user.id,
            recommendation_type="scheme_suggestion",
            reasoning="NPS offers an additional Rs. 50,000 deduction under 80CCD(1B).",
            confidence_score=0.95,
            alternatives_considered=[{"option": "PPF", "reason": "lower ceiling"}],
            assumptions_used={"regime": "old"},
        )
        db.add(recommendation)
        await db.flush()

        citation = RecommendationCitation(
            recommendation_id=recommendation.id, scheme_id=scheme.id
        )
        db.add(citation)
        await db.flush()

        result = await db.execute(
            select(Recommendation).where(Recommendation.user_id == user.id)
        )
        stored = result.scalar_one()
        assert stored.confidence_score == pytest.approx(0.95)
        assert stored.alternatives_considered == [{"option": "PPF", "reason": "lower ceiling"}]
        assert stored.assumptions_used == {"regime": "old"}

    async def test_audit_log_captures_before_after_state(
        self, db: AsyncSession, user: User
    ) -> None:
        log = AuditLog(
            user_id=user.id,
            action="huf_created",
            before_state=None,
            after_state={"funding_source": "ancestral_property"},
        )
        db.add(log)
        await db.flush()

        result = await db.execute(select(AuditLog).where(AuditLog.user_id == user.id))
        stored = result.scalar_one()
        assert stored.action == "huf_created"
        assert stored.after_state == {"funding_source": "ancestral_property"}
        assert isinstance(stored.created_at, datetime)
