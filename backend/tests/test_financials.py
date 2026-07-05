"""Integration tests for financial data endpoints (income, expenses, assets, liabilities, assumptions, profile)."""

import pytest
from httpx import AsyncClient


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

    async def test_delete_nonexistent_income(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete(
            "/api/v1/financials/income/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_income_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/financials/income")
        assert resp.status_code == 403


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
