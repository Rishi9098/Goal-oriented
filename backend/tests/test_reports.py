"""Integration tests for the Reports endpoint."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

GOAL_PAYLOAD = {
    "name": "Retirement",
    "category": "retirement",
    "target_amount": 500_000,
    "current_amount": 10_000,
    "target_date": (date.today() + timedelta(days=365 * 20)).isoformat(),
    "monthly_contribution": 500,
    "risk_profile": "balanced",
    "priority": 1,
}

SECOND_GOAL_PAYLOAD = {
    "name": "Home Purchase",
    "category": "home",
    "target_amount": 120_000,
    "current_amount": 30_000,
    "target_date": (date.today() + timedelta(days=365 * 5)).isoformat(),
    "monthly_contribution": 800,
    "risk_profile": "conservative",
    "priority": 2,
}


@pytest.mark.asyncio
class TestReports:
    async def test_summary_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/reports/summary")
        assert resp.status_code == 403

    async def test_summary_empty_user_returns_200(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/reports/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["goal_count"] == 0
        assert data["goals"] == []
        assert data["plan_health_score"] == 0

    async def test_summary_contains_required_fields(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/reports/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        required = [
            "generated_at",
            "plan_health_score",
            "net_worth",
            "liquid_assets",
            "invested",
            "liabilities",
            "monthly_income",
            "monthly_expenses",
            "monthly_savings_rate",
            "goal_count",
            "goals_on_track",
            "goals",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    async def test_summary_reflects_created_goals(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        resp = await client.get("/api/v1/reports/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["goal_count"] == 1
        assert len(data["goals"]) == 1
        goal = data["goals"][0]
        assert goal["name"] == "Retirement"
        assert goal["category"] == "retirement"
        assert goal["target_amount"] == 500_000
        assert 0 <= goal["probability"] <= 100
        assert isinstance(goal["on_track"], bool)

    async def test_summary_with_multiple_goals(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        await client.post("/api/v1/goals", json=SECOND_GOAL_PAYLOAD, headers=auth_headers)
        resp = await client.get("/api/v1/reports/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["goal_count"] == 2
        assert len(data["goals"]) == 2
        assert 0 <= data["plan_health_score"] <= 100

    async def test_summary_goal_items_have_required_fields(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        resp = await client.get("/api/v1/reports/summary", headers=auth_headers)
        goal = resp.json()["goals"][0]
        for field in ["id", "name", "category", "target_amount", "current_amount",
                      "monthly_contribution", "probability", "on_track", "target_date"]:
            assert field in goal, f"Missing goal field: {field}"

    async def test_summary_generated_at_is_recent(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        from datetime import UTC, datetime
        resp = await client.get("/api/v1/reports/summary", headers=auth_headers)
        generated = datetime.fromisoformat(resp.json()["generated_at"])
        now = datetime.now(UTC)
        diff = abs((now - generated).total_seconds())
        assert diff < 10

    async def test_dashboard_and_reports_show_identical_probability(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """PCA-3 / ADR-001: Dashboard and Reports must read the same persisted
        value for identical inputs, never two independent simulation runs."""
        await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)

        dashboard_resp = await client.get("/api/v1/dashboard", headers=auth_headers)
        reports_resp = await client.get("/api/v1/reports/summary", headers=auth_headers)

        dashboard_data = dashboard_resp.json()
        reports_data = reports_resp.json()
        assert dashboard_data["plan_health_score"] == reports_data["plan_health_score"]
        assert dashboard_data["goals_on_track"] == reports_data["goals_on_track"]
