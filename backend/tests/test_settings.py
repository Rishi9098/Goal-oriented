"""Integration tests for change-password and delete-account endpoints."""

import pytest
from httpx import AsyncClient

_REGISTER_PAYLOAD = {
    "email": "settings@example.com",
    "password": "Password1!",
    "full_name": "Settings User",
}


@pytest.mark.asyncio
class TestChangePassword:
    async def test_change_password_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Password1!", "new_password": "NewPass2!"},
        )
        assert resp.status_code == 403

    async def test_change_password_success(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Password1!", "new_password": "NewPass2@"},
            headers=headers,
        )
        assert resp.status_code == 204

    async def test_change_password_wrong_current_rejected(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "WrongPass!", "new_password": "NewPass2@"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["detail"].lower()

    async def test_change_password_same_as_current_rejected(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Password1!", "new_password": "Password1!"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "differ" in resp.json()["detail"].lower()

    async def test_change_password_too_short_rejected(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Password1!", "new_password": "short"},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_new_password_works_for_login(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Password1!", "new_password": "NewPass2@"},
            headers=headers,
        )

        new_login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": "NewPass2@"},
        )
        assert new_login.status_code == 200
        assert "access_token" in new_login.json()


@pytest.mark.asyncio
class TestDeleteAccount:
    async def test_delete_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/v1/auth/me")
        assert resp.status_code == 403

    async def test_delete_returns_204(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.delete("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 204

    async def test_deleted_account_cannot_login(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.delete("/api/v1/auth/me", headers=headers)

        retry = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        assert retry.status_code == 403

    async def test_deleted_account_token_rejected(self, client: AsyncClient) -> None:
        await client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.delete("/api/v1/auth/me", headers=headers)

        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code in (401, 403)
