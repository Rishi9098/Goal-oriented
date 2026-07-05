"""Integration tests for simulate and optimize endpoints."""

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

SIM_PAYLOAD = {
    "initial_amount": 10_000,
    "monthly_contribution": 500,
    "years_to_goal": 20,
    "risk_profile": "balanced",
    "num_simulations": 1_000,
}


@pytest.mark.asyncio
class TestSimulate:
    async def test_simulate_returns_201(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/simulate", json=SIM_PAYLOAD, headers=auth_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert 0 <= data["success_rate"] <= 100
        assert "percentiles" in data
        assert "distribution" in data

    async def test_simulate_percentile_ordering(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/simulate", json=SIM_PAYLOAD, headers=auth_headers
        )
        p = resp.json()["percentiles"]
        assert p["p10"] <= p["p25"] <= p["p50"] <= p["p75"] <= p["p90"]

    async def test_simulate_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/simulate", json=SIM_PAYLOAD)
        assert resp.status_code == 403

    async def test_simulate_aggressive_profile(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        payload = {**SIM_PAYLOAD, "risk_profile": "aggressive"}
        resp = await client.post(
            "/api/v1/simulate", json=payload, headers=auth_headers
        )
        assert resp.status_code == 201
        assert 0 <= resp.json()["success_rate"] <= 100

    async def test_simulate_with_goal_id_uses_goal_target(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        goal_resp = await client.post(
            "/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers
        )
        assert goal_resp.status_code == 201
        goal_id = goal_resp.json()["id"]

        payload = {**SIM_PAYLOAD, "goal_id": goal_id, "num_simulations": 1_000}
        resp = await client.post(
            "/api/v1/simulate", json=payload, headers=auth_headers
        )
        assert resp.status_code == 201
        assert 0 <= resp.json()["success_rate"] <= 100


@pytest.mark.asyncio
class TestOptimize:
    async def _create_goal(
        self, client: AsyncClient, auth_headers: dict
    ) -> str:
        resp = await client.post(
            "/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_optimize_returns_suggestions(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        goal_id = await self._create_goal(client, auth_headers)
        resp = await client.post(
            "/api/v1/simulate/optimize",
            json={"goal_id": goal_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) >= 1

    async def test_optimize_nonexistent_goal_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        import uuid

        resp = await client.post(
            "/api/v1/simulate/optimize",
            json={"goal_id": str(uuid.uuid4())},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_optimize_requires_auth(self, client: AsyncClient) -> None:
        import uuid

        resp = await client.post(
            "/api/v1/simulate/optimize", json={"goal_id": str(uuid.uuid4())}
        )
        assert resp.status_code == 403
