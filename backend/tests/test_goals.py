"""Integration tests for the Goals API."""

import pytest
from httpx import AsyncClient

GOAL_PAYLOAD = {
    "name": "Emergency Fund",
    "category": "emergency",
    "target_amount": 50000,
    "current_amount": 10000,
    "target_date": "2027-01-01",
    "monthly_contribution": 1000,
    "risk_profile": "conservative",
    "priority": 1,
}


@pytest.mark.asyncio
class TestGoalsCRUD:
    async def test_create_goal(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == GOAL_PAYLOAD["name"]
        assert "id" in data
        assert "probability" in data
        assert "on_track" in data

    async def test_list_goals_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/goals", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_goals_after_create(self, client: AsyncClient, auth_headers: dict):
        await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        resp = await client.get("/api/v1/goals", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_get_goal_by_id(self, client: AsyncClient, auth_headers: dict):
        create = await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        goal_id = create.json()["id"]
        resp = await client.get(f"/api/v1/goals/{goal_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == goal_id

    async def test_get_nonexistent_goal(self, client: AsyncClient, auth_headers: dict):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(f"/api/v1/goals/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_update_goal(self, client: AsyncClient, auth_headers: dict):
        create = await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        goal_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/goals/{goal_id}",
            json={"name": "Updated Fund", "monthly_contribution": 2000},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Fund"
        assert resp.json()["monthly_contribution"] == 2000

    async def test_delete_goal(self, client: AsyncClient, auth_headers: dict):
        create = await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        goal_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/goals/{goal_id}", headers=auth_headers)
        assert resp.status_code == 204
        # Soft-deleted — should not appear in list
        list_resp = await client.get("/api/v1/goals", headers=auth_headers)
        assert all(g["id"] != goal_id for g in list_resp.json())

    async def test_goals_isolated_between_users(self, client: AsyncClient):
        # Two separate users
        for email in ("u1@ex.com", "u2@ex.com"):
            await client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "Pass12345!"},
            )

        login1 = await client.post(
            "/api/v1/auth/login", json={"email": "u1@ex.com", "password": "Pass12345!"}
        )
        login2 = await client.post(
            "/api/v1/auth/login", json={"email": "u2@ex.com", "password": "Pass12345!"}
        )
        h1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}
        h2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=h1)
        goals_u2 = await client.get("/api/v1/goals", headers=h2)
        assert goals_u2.json() == []

    async def test_unauthenticated_access(self, client: AsyncClient):
        resp = await client.get("/api/v1/goals")
        assert resp.status_code == 403

    async def test_invalid_goal_category(self, client: AsyncClient, auth_headers: dict):
        payload = {**GOAL_PAYLOAD, "category": "invalid_cat"}
        resp = await client.post("/api/v1/goals", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_negative_target_amount_rejected(self, client: AsyncClient, auth_headers: dict):
        payload = {**GOAL_PAYLOAD, "target_amount": -1000}
        resp = await client.post("/api/v1/goals", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_absurdly_large_target_amount_rejected(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        # AUDIT.md #10: unbounded amounts can drive the Monte Carlo engine's
        # compounding loop to inf/NaN.
        payload = {**GOAL_PAYLOAD, "target_amount": 1e18}
        resp = await client.post("/api/v1/goals", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_absurdly_large_monthly_contribution_rejected(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        payload = {**GOAL_PAYLOAD, "monthly_contribution": 1e12}
        resp = await client.post("/api/v1/goals", json=payload, headers=auth_headers)
        assert resp.status_code == 422
