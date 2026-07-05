"""Integration tests for the dashboard endpoint and planning service."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDashboard:
    async def test_empty_dashboard(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["goal_count"] == 0
        assert "plan_health_score" in data
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    async def test_dashboard_with_goals(self, client: AsyncClient, auth_headers: dict) -> None:
        goal_payload = {
            "name": "Emergency Fund",
            "category": "emergency",
            "target_amount": 20_000,
            "current_amount": 5_000,
            "target_date": (date.today() + timedelta(days=365 * 3)).isoformat(),
            "monthly_contribution": 300,
            "risk_profile": "conservative",
            "priority": 1,
        }
        await client.post("/api/v1/goals", json=goal_payload, headers=auth_headers)

        resp = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["goal_count"] == 1
        assert "plan_health_score" in data
        assert "goals_on_track" in data
        assert "suggestions" in data

    async def test_dashboard_suggestions_include_no_retirement(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        goal_payload = {
            "name": "Emergency Fund",
            "category": "emergency",
            "target_amount": 20_000,
            "current_amount": 5_000,
            "target_date": (date.today() + timedelta(days=365 * 2)).isoformat(),
            "monthly_contribution": 500,
            "risk_profile": "conservative",
            "priority": 1,
        }
        await client.post("/api/v1/goals", json=goal_payload, headers=auth_headers)
        resp = await client.get("/api/v1/dashboard", headers=auth_headers)
        suggestions = resp.json()["suggestions"]
        ids = [s["id"] for s in suggestions]
        assert "no_retirement" in ids

    async def test_dashboard_net_worth_from_assets_and_liabilities(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post(
            "/api/v1/financials/assets",
            json={"asset_type": "checking", "current_value": 50_000},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/financials/assets",
            json={"asset_type": "brokerage", "current_value": 100_000},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/financials/liabilities",
            json={"liability_type": "student_loan", "balance": 30_000},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["net_worth"] == pytest.approx(120_000)
        assert data["liquid_assets"] == pytest.approx(50_000)
        assert data["invested"] == pytest.approx(100_000)
        assert data["liabilities"] == pytest.approx(30_000)

    async def test_dashboard_savings_rate_from_income_and_expenses(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post(
            "/api/v1/financials/income",
            json={"source_type": "salary", "annual_amount": 120_000},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/financials/expenses",
            json={"category": "housing", "monthly_amount": 3_000},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # monthly income = 10_000, expenses = 3_000, savings = 7_000 → rate = 70%
        assert data["monthly_savings_rate"] == pytest.approx(70.0, abs=1.0)

    async def test_dashboard_low_savings_rate_suggestion(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        # income $24k/year → $2k/month; expenses $1.9k/month → savings rate ~5%
        await client.post(
            "/api/v1/financials/income",
            json={"source_type": "salary", "annual_amount": 24_000},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/financials/expenses",
            json={"category": "housing", "monthly_amount": 1_900},
            headers=auth_headers,
        )
        # add an asset so the code takes the non-fallback path
        await client.post(
            "/api/v1/financials/assets",
            json={"asset_type": "checking", "current_value": 1_000},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        ids = [s["id"] for s in data["suggestions"]]
        assert "low_savings_rate" in ids

    async def test_dashboard_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 403
