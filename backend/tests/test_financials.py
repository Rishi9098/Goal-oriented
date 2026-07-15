"""Integration tests for financial data endpoints (income, expenses, assets, liabilities, assumptions, profile)."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assumptions import FinancialAssumptions
from app.models.user import User
from tests.conftest import TestSessionLocal


@pytest.mark.asyncio
class TestIncome:
    async def test_list_income_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/financials/income", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_income(self, client: AsyncClient, auth_headers: dict):
        payload = {"source_type": "salary", "description": "Day job", "annual_amount": 120000}
        resp = await client.post("/api/v1/financials/income", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["annual_amount"] == 120000
        assert data["source_type"] == "salary"
        assert "id" in data

    async def test_list_income_after_create(self, client: AsyncClient, auth_headers: dict):
        payload = {"source_type": "rental", "annual_amount": 24000}
        await client.post("/api/v1/financials/income", json=payload, headers=auth_headers)
        resp = await client.get("/api/v1/financials/income", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_delete_income(self, client: AsyncClient, auth_headers: dict):
        payload = {"source_type": "dividends", "annual_amount": 5000}
        create = await client.post("/api/v1/financials/income", json=payload, headers=auth_headers)
        income_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/financials/income/{income_id}", headers=auth_headers)
        assert resp.status_code == 204
        list_resp = await client.get("/api/v1/financials/income", headers=auth_headers)
        assert list_resp.json() == []

    async def test_update_income(self, client: AsyncClient, auth_headers: dict):
        payload = {"source_type": "salary", "annual_amount": 120000}
        create = await client.post("/api/v1/financials/income", json=payload, headers=auth_headers)
        income_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/financials/income/{income_id}",
            json={"annual_amount": 130000},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["annual_amount"] == 130000

    async def test_update_income_ignores_source_type(
        self, client: AsyncClient, auth_headers: dict
    ):
        payload = {"source_type": "salary", "annual_amount": 120000}
        create = await client.post("/api/v1/financials/income", json=payload, headers=auth_headers)
        income_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/financials/income/{income_id}",
            json={"source_type": "bonus", "annual_amount": 121000},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_type"] == "salary"
        assert data["annual_amount"] == 121000

    async def test_update_nonexistent_income(self, client: AsyncClient, auth_headers: dict):
        resp = await client.patch(
            "/api/v1/financials/income/00000000-0000-0000-0000-000000000000",
            json={"annual_amount": 1000},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_deleted_income_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        payload = {"source_type": "salary", "annual_amount": 120000}
        create = await client.post("/api/v1/financials/income", json=payload, headers=auth_headers)
        income_id = create.json()["id"]
        await client.delete(f"/api/v1/financials/income/{income_id}", headers=auth_headers)
        resp = await client.patch(
            f"/api/v1/financials/income/{income_id}",
            json={"annual_amount": 1000},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_delete_nonexistent_income(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete(
            "/api/v1/financials/income/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_income_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/financials/income")
        assert resp.status_code == 403

    async def test_absurdly_large_annual_amount_rejected(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        # AUDIT.md #10: unbounded amounts can drive the Monte Carlo engine's
        # compounding loop to inf/NaN.
        payload = {"source_type": "salary", "annual_amount": 1e15}
        resp = await client.post("/api/v1/financials/income", json=payload, headers=auth_headers)
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestExpenses:
    async def test_create_expense(self, client: AsyncClient, auth_headers: dict):
        payload = {"category": "housing", "description": "Rent", "monthly_amount": 2500}
        resp = await client.post("/api/v1/financials/expenses", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["monthly_amount"] == 2500
        assert data["category"] == "housing"

    async def test_list_expenses(self, client: AsyncClient, auth_headers: dict):
        payloads = [
            {"category": "food", "monthly_amount": 800},
            {"category": "transport", "monthly_amount": 400},
        ]
        for p in payloads:
            await client.post("/api/v1/financials/expenses", json=p, headers=auth_headers)
        resp = await client.get("/api/v1/financials/expenses", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_delete_expense(self, client: AsyncClient, auth_headers: dict):
        payload = {"category": "entertainment", "monthly_amount": 150}
        create = await client.post("/api/v1/financials/expenses", json=payload, headers=auth_headers)
        expense_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/financials/expenses/{expense_id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_update_expense(self, client: AsyncClient, auth_headers: dict):
        payload = {"category": "housing", "monthly_amount": 2400}
        create = await client.post(
            "/api/v1/financials/expenses", json=payload, headers=auth_headers
        )
        expense_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/financials/expenses/{expense_id}",
            json={"monthly_amount": 2500, "description": "Rent (incl. parking)"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["monthly_amount"] == 2500
        assert data["description"] == "Rent (incl. parking)"

    async def test_update_expense_ignores_category(
        self, client: AsyncClient, auth_headers: dict
    ):
        payload = {"category": "housing", "monthly_amount": 2400}
        create = await client.post(
            "/api/v1/financials/expenses", json=payload, headers=auth_headers
        )
        expense_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/financials/expenses/{expense_id}",
            json={"category": "food", "monthly_amount": 2450},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "housing"
        assert data["monthly_amount"] == 2450

    async def test_update_nonexistent_expense(self, client: AsyncClient, auth_headers: dict):
        resp = await client.patch(
            "/api/v1/financials/expenses/00000000-0000-0000-0000-000000000000",
            json={"monthly_amount": 100},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_absurdly_large_monthly_amount_rejected(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        payload = {"category": "housing", "monthly_amount": 1e12}
        resp = await client.post("/api/v1/financials/expenses", json=payload, headers=auth_headers)
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestAssets:
    async def test_create_asset(self, client: AsyncClient, auth_headers: dict):
        payload = {"asset_type": "checking", "institution": "Chase", "current_value": 15000}
        resp = await client.post("/api/v1/financials/assets", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["current_value"] == 15000
        assert data["asset_type"] == "checking"

    async def test_update_asset(self, client: AsyncClient, auth_headers: dict):
        payload = {"asset_type": "savings", "current_value": 30000}
        create = await client.post("/api/v1/financials/assets", json=payload, headers=auth_headers)
        asset_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/financials/assets/{asset_id}",
            json={"current_value": 35000},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_value"] == 35000

    async def test_delete_asset(self, client: AsyncClient, auth_headers: dict):
        payload = {"asset_type": "brokerage", "current_value": 50000}
        create = await client.post("/api/v1/financials/assets", json=payload, headers=auth_headers)
        asset_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/financials/assets/{asset_id}", headers=auth_headers)
        assert resp.status_code == 204
        list_resp = await client.get("/api/v1/financials/assets", headers=auth_headers)
        assert list_resp.json() == []

    async def test_update_nonexistent_asset(self, client: AsyncClient, auth_headers: dict):
        resp = await client.patch(
            "/api/v1/financials/assets/00000000-0000-0000-0000-000000000000",
            json={"current_value": 999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_absurdly_large_current_value_rejected(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        payload = {"asset_type": "brokerage", "current_value": 1e18}
        resp = await client.post("/api/v1/financials/assets", json=payload, headers=auth_headers)
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestLiabilities:
    async def test_create_liability(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "liability_type": "mortgage",
            "institution": "Wells Fargo",
            "balance": 350000,
            "interest_rate": 0.065,
            "monthly_payment": 2100,
        }
        resp = await client.post("/api/v1/financials/liabilities", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["balance"] == 350000
        assert data["liability_type"] == "mortgage"

    async def test_update_liability_balance(self, client: AsyncClient, auth_headers: dict):
        payload = {"liability_type": "student_loan", "balance": 45000, "monthly_payment": 500}
        create = await client.post("/api/v1/financials/liabilities", json=payload, headers=auth_headers)
        lid = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/financials/liabilities/{lid}",
            json={"balance": 44500},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["balance"] == 44500

    async def test_delete_liability(self, client: AsyncClient, auth_headers: dict):
        payload = {"liability_type": "credit_card", "balance": 5000, "monthly_payment": 200}
        create = await client.post("/api/v1/financials/liabilities", json=payload, headers=auth_headers)
        lid = create.json()["id"]
        resp = await client.delete(f"/api/v1/financials/liabilities/{lid}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_absurdly_large_balance_rejected(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        payload = {"liability_type": "mortgage", "balance": 1e18}
        resp = await client.post(
            "/api/v1/financials/liabilities", json=payload, headers=auth_headers
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestAssumptions:
    async def test_get_assumptions_creates_defaults(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/assumptions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["inflation_rate"] == 0.03
        assert data["retirement_age"] == 65
        assert data["expected_return_balanced"] == 0.07

    async def test_get_assumptions_idempotent(self, client: AsyncClient, auth_headers: dict):
        r1 = await client.get("/api/v1/assumptions", headers=auth_headers)
        r2 = await client.get("/api/v1/assumptions", headers=auth_headers)
        assert r1.json()["id"] == r2.json()["id"]

    async def test_update_assumptions(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(
            "/api/v1/assumptions",
            json={"inflation_rate": 0.04, "retirement_age": 67},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["inflation_rate"] == 0.04
        assert data["retirement_age"] == 67
        assert data["expected_return_balanced"] == 0.07

    async def test_assumptions_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/assumptions")
        assert resp.status_code == 403

    async def test_get_assumptions_concurrent_first_access_does_not_error(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db: AsyncSession,
        user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Simulates two near-simultaneous first-access requests for a user
        with no saved assumptions yet: this request's own insert collides
        with one a concurrent request already committed. The fix in
        app.routers.assumptions.get_assumptions must recover by returning
        the already-created row instead of propagating the database's
        unique-constraint error (Milestone1ImplementationSpecification_
        FINAL.md §9). A second, independent session simulates the winning
        concurrent request; `db.flush` is forced to fail once to reproduce
        the exact ordering a real race would produce, since ordering that
        precisely can't be reproduced by timing alone against one shared
        test session.
        """
        async with TestSessionLocal() as other_session:
            other_session.add(
                FinancialAssumptions(
                    user_id=user.id,
                    inflation_rate=0.03,
                    expected_return_conservative=0.05,
                    expected_return_balanced=0.07,
                    expected_return_aggressive=0.09,
                    tax_rate=0.22,
                    retirement_age=65,
                    social_security_monthly=0.0,
                )
            )
            await other_session.commit()

        async def force_integrity_error(*args: object, **kwargs: object) -> None:
            raise IntegrityError("insert", {}, Exception("UNIQUE constraint failed"))

        monkeypatch.setattr(db, "flush", force_integrity_error)

        resp = await client.get("/api/v1/assumptions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["inflation_rate"] == 0.03
        assert data["retirement_age"] == 65


@pytest.mark.asyncio
class TestProfile:
    async def test_get_profile_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/profile", headers=auth_headers)
        assert resp.status_code == 404

    async def test_create_profile_via_put(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "date_of_birth": "1990-06-15",
            "employment_status": "employed",
            "dependents": 1,
            "country": "US",
        }
        resp = await client.put("/api/v1/profile", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["employment_status"] == "employed"
        assert data["dependents"] == 1
        assert data["onboarding_complete"] is False

    async def test_update_profile_via_put(self, client: AsyncClient, auth_headers: dict):
        await client.put("/api/v1/profile", json={"dependents": 0}, headers=auth_headers)
        resp = await client.put(
            "/api/v1/profile",
            json={"dependents": 2, "onboarding_complete": True, "current_step": 12},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dependents"] == 2
        assert data["onboarding_complete"] is True
        assert data["current_step"] == 12

    async def test_get_profile_after_create(self, client: AsyncClient, auth_headers: dict):
        await client.put("/api/v1/profile", json={"country": "CA"}, headers=auth_headers)
        resp = await client.get("/api/v1/profile", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["country"] == "CA"


@pytest.mark.asyncio
class TestFinancialsDoNotAffectGoalCalculations:
    """The single most important test in Milestone 1
    (Milestone1ImplementationSpecification_FINAL.md §15): none of the fields
    this milestone makes editable — income, expense, asset, and liability
    values, or planning assumptions — are part of the Monte Carlo
    Calculation Context, so creating, editing, or deleting any of them must
    never change an existing goal's stored probability.
    """

    async def test_income_expense_asset_liability_and_assumptions_changes_do_not_alter_goal_probability(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        goal_payload = {
            "name": "Retire Comfortably",
            "category": "retirement",
            "target_amount": 500000,
            "current_amount": 10000,
            "target_date": (date.today() + timedelta(days=365 * 20)).isoformat(),
            "monthly_contribution": 500,
            "risk_profile": "balanced",
            "priority": 1,
        }
        create_goal = await client.post("/api/v1/goals", json=goal_payload, headers=auth_headers)
        assert create_goal.status_code == 201
        goal_id = create_goal.json()["id"]
        probability_before = create_goal.json()["probability"]

        income = await client.post(
            "/api/v1/financials/income",
            json={"source_type": "salary", "annual_amount": 120000},
            headers=auth_headers,
        )
        await client.patch(
            f"/api/v1/financials/income/{income.json()['id']}",
            json={"annual_amount": 200000},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/financials/expenses",
            json={"category": "housing", "monthly_amount": 2400},
            headers=auth_headers,
        )
        asset = await client.post(
            "/api/v1/financials/assets",
            json={"asset_type": "checking", "current_value": 8500},
            headers=auth_headers,
        )
        await client.patch(
            f"/api/v1/financials/assets/{asset.json()['id']}",
            json={"current_value": 500000},
            headers=auth_headers,
        )
        liability = await client.post(
            "/api/v1/financials/liabilities",
            json={"liability_type": "mortgage", "balance": 310000, "monthly_payment": 1850},
            headers=auth_headers,
        )
        await client.delete(
            f"/api/v1/financials/liabilities/{liability.json()['id']}", headers=auth_headers
        )
        await client.put(
            "/api/v1/assumptions", json={"inflation_rate": 0.08}, headers=auth_headers
        )

        goals_after = await client.get("/api/v1/goals", headers=auth_headers)
        assert goals_after.status_code == 200
        goal_after = next(g for g in goals_after.json() if g["id"] == goal_id)
        assert goal_after["probability"] == probability_before
