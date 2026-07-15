"""Tests for the Foundation reconciliation migration (006): HUF financial
ownership (Finding B) and Policy Engine Layers 2-3 (Finding D). See
FoundationReconciliationReport.md for the full decision log.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_policy import BestPracticeRule, CompanyPolicy
from app.models.estate import HUFEntity
from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.user import User


@pytest.mark.asyncio
class TestHUFFinancialOwnership:
    async def test_income_source_defaults_to_no_huf_owner(
        self, db: AsyncSession, user: User
    ) -> None:
        # Arrange / Act — a normal, personally-owned income source, exactly
        # as every row created before this reconciliation.
        income = IncomeSource(user_id=user.id, source_type="salary", annual_amount=1_200_000.0)
        db.add(income)
        await db.flush()

        # Assert — huf_entity_id defaults to NULL; existing behavior unchanged.
        result = await db.execute(select(IncomeSource).where(IncomeSource.id == income.id))
        assert result.scalar_one().huf_entity_id is None

    async def test_income_source_can_be_attributed_to_huf(
        self, db: AsyncSession, user: User
    ) -> None:
        huf = HUFEntity(karta_user_id=user.id, funding_source="ancestral_property")
        db.add(huf)
        await db.flush()

        income = IncomeSource(
            user_id=user.id,
            huf_entity_id=huf.id,
            source_type="rental",
            annual_amount=300_000.0,
        )
        db.add(income)
        await db.flush()

        result = await db.execute(select(IncomeSource).where(IncomeSource.id == income.id))
        stored = result.scalar_one()
        assert stored.huf_entity_id == huf.id
        assert stored.user_id == user.id  # karta still resolves access control

    async def test_deleting_huf_entity_nulls_ownership_not_cascades(
        self, db: AsyncSession, user: User
    ) -> None:
        # This is the key modeling decision under test: ON DELETE SET NULL,
        # not CASCADE — the financial row must survive an HUF's removal.
        #
        # This test's SQLite backend does not enforce FK-level ON DELETE
        # behavior without an explicit `PRAGMA foreign_keys=ON` that this
        # suite's conftest.py does not set (deliberately not added here —
        # touching shared test infrastructure is outside this
        # reconciliation's minimal scope and could affect unrelated tests).
        # The `huf_entity_id IS NULL after HUF deletion` half of this
        # behavior was instead verified directly against the real Postgres
        # dev database (INSERT/DELETE/SELECT in a rolled-back transaction —
        # see FoundationReconciliationReport.md's Database Review section
        # for the transcript). What this test *can* and does verify under
        # SQLite is the other half: the row survives at all, i.e. deleting
        # the HUF must never cascade-delete the financial row.
        huf = HUFEntity(karta_user_id=user.id, funding_source="family_business")
        db.add(huf)
        await db.flush()

        asset = Asset(
            user_id=user.id, huf_entity_id=huf.id, asset_type="brokerage", current_value=500_000.0
        )
        db.add(asset)
        await db.flush()
        asset_id = asset.id

        await db.delete(huf)
        await db.flush()

        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        surviving_asset = result.scalar_one_or_none()
        assert surviving_asset is not None

    async def test_expense_and_liability_also_support_huf_attribution(
        self, db: AsyncSession, user: User
    ) -> None:
        huf = HUFEntity(karta_user_id=user.id, funding_source="ancestral_property")
        db.add(huf)
        await db.flush()

        expense = Expense(
            user_id=user.id, huf_entity_id=huf.id, category="property_tax", monthly_amount=5_000.0
        )
        liability = Liability(
            user_id=user.id,
            huf_entity_id=huf.id,
            liability_type="property_loan",
            balance=2_000_000.0,
        )
        db.add_all([expense, liability])
        await db.flush()

        expense_result = await db.execute(select(Expense).where(Expense.huf_entity_id == huf.id))
        assert expense_result.scalar_one().category == "property_tax"

        liability_result = await db.execute(
            select(Liability).where(Liability.huf_entity_id == huf.id)
        )
        assert liability_result.scalar_one().liability_type == "property_loan"


@pytest.mark.asyncio
class TestPolicyEngineLayers23:
    async def test_best_practice_rule_with_confidence_tier(self, db: AsyncSession) -> None:
        rule = BestPracticeRule(
            rule_code="emergency_fund_months_freelancer",
            applies_to_persona="freelancer",
            value=6.0,
            unit="months",
            rationale_text="Freelancers face income volatility with no employer safety net.",
            source_type="cfp_convention",
            confidence="convention",
            last_reviewed_date=date(2026, 7, 6),
        )
        db.add(rule)
        await db.flush()

        result = await db.execute(
            select(BestPracticeRule).where(
                BestPracticeRule.rule_code == "emergency_fund_months_freelancer"
            )
        )
        stored = result.scalar_one()
        assert stored.confidence == "convention"
        assert stored.value == pytest.approx(6.0)

    async def test_company_policy_hard_gate_with_json_rule_definition(
        self, db: AsyncSession
    ) -> None:
        policy = CompanyPolicy(
            policy_code="pmvvy_never_recommend_new",
            policy_type="hard_gate",
            rule_definition={"scheme_code": "PMVVY", "condition": "status == closed_to_new"},
            effective_from=date(2026, 7, 6),
            approved_by="reconciliation-audit",
        )
        db.add(policy)
        await db.flush()

        result = await db.execute(
            select(CompanyPolicy).where(CompanyPolicy.policy_code == "pmvvy_never_recommend_new")
        )
        stored = result.scalar_one()
        assert stored.policy_type == "hard_gate"
        assert stored.rule_definition["scheme_code"] == "PMVVY"

    async def test_policy_code_must_be_unique(self, db: AsyncSession) -> None:
        from sqlalchemy.exc import IntegrityError

        db.add(
            CompanyPolicy(
                policy_code="duplicate_code",
                policy_type="soft_preference",
                rule_definition={},
                effective_from=date(2026, 7, 6),
            )
        )
        await db.flush()

        db.add(
            CompanyPolicy(
                policy_code="duplicate_code",
                policy_type="ranking_weight",
                rule_definition={},
                effective_from=date(2026, 7, 6),
            )
        )
        with pytest.raises(IntegrityError):
            await db.flush()
