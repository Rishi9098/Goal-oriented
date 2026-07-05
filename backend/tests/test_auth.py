"""Integration tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    async def test_register_new_user(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "StrongPass1!"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert "id" in data
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "password": "StrongPass1!"}
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "short"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_valid_credentials(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "ValidPass1!"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "ValidPass1!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        # Regression guard for AUDIT #4: the refresh token must never appear
        # in the JSON body — it belongs only in the httpOnly cookie.
        assert "refresh_token" not in data
        assert data["token_type"] == "bearer"
        assert client.cookies.get("ns_refresh_token") is not None
        assert client.cookies.get("ns_csrf_token") is not None

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "wrong@example.com", "password": "ValidPass1!"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "WrongPass1!"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "AnyPass1!"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestRefresh:
    async def _login(self, client: AsyncClient, email: str = "refresh@example.com") -> None:
        await client.post(
            "/api/v1/auth/register", json={"email": email, "password": "ValidPass1!"}
        )
        await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "ValidPass1!"}
        )

    async def test_refresh_returns_new_access_token(self, client: AsyncClient):
        await self._login(client)
        csrf = client.cookies["ns_csrf_token"]
        resp = await client.post(
            "/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf}
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert "refresh_token" not in resp.json()

    async def test_refresh_rotates_csrf_cookie(self, client: AsyncClient):
        await self._login(client)
        first_csrf = client.cookies["ns_csrf_token"]
        await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": first_csrf})
        assert client.cookies["ns_csrf_token"] != first_csrf

    async def test_refresh_without_session_cookie_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "x"})
        assert resp.status_code == 401

    async def test_refresh_without_csrf_header_returns_403(self, client: AsyncClient):
        await self._login(client)
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 403

    async def test_refresh_with_mismatched_csrf_header_returns_403(self, client: AsyncClient):
        await self._login(client)
        resp = await client.post(
            "/api/v1/auth/refresh", headers={"X-CSRF-Token": "not-the-real-token"}
        )
        assert resp.status_code == 403

    async def test_refresh_invalid_refresh_token_returns_401(self, client: AsyncClient):
        client.cookies.set("ns_refresh_token", "not.a.valid.token", path="/api/v1/auth")
        client.cookies.set("ns_csrf_token", "matching-csrf-value", path="/")
        resp = await client.post(
            "/api/v1/auth/refresh", headers={"X-CSRF-Token": "matching-csrf-value"}
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestLogout:
    async def test_logout_clears_refresh_session(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "logout@example.com", "password": "ValidPass1!"},
        )
        await client.post(
            "/api/v1/auth/login",
            json={"email": "logout@example.com", "password": "ValidPass1!"},
        )
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 204
        assert client.cookies.get("ns_refresh_token") is None

        # The cleared cookie means refresh can no longer succeed.
        refresh = await client.post(
            "/api/v1/auth/refresh", headers={"X-CSRF-Token": "whatever"}
        )
        assert refresh.status_code == 401


@pytest.mark.asyncio
class TestMe:
    async def test_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 403

    async def test_update_full_name(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(
            "/api/v1/auth/me",
            json={"full_name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    async def test_update_me_persists(self, client: AsyncClient, auth_headers: dict):
        await client.put(
            "/api/v1/auth/me",
            json={"full_name": "Persisted Name"},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.json()["full_name"] == "Persisted Name"

    async def test_update_password(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(
            "/api/v1/auth/me",
            json={"password": "NewStrongPass9!"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_update_me_unauthenticated(self, client: AsyncClient):
        resp = await client.put("/api/v1/auth/me", json={"full_name": "X"})
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestForgotResetPassword:
    _EMAIL = "reset@example.com"
    _PASS = "ValidPass1!"

    async def _register(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={"email": self._EMAIL, "password": self._PASS},
        )

    async def test_forgot_password_unknown_email_returns_200(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200
        assert "message" in resp.json()
        assert resp.json().get("reset_token") is None

    async def test_forgot_password_known_email_does_not_leak_token(
        self, client: AsyncClient
    ) -> None:
        # Regression test: the response must never hand back the reset token
        # itself outside of debug builds, or anyone who knows a user's email
        # can reset their password without ever receiving the "sent" email.
        await self._register(client)
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": self._EMAIL},
        )
        assert resp.status_code == 200
        assert resp.json().get("reset_token") is None

    async def test_reset_password_with_valid_token(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        known_token = "test-fixed-reset-token-0123456789"
        monkeypatch.setattr(
            "app.routers.auth.secrets.token_urlsafe", lambda *_: known_token
        )

        await self._register(client)
        forgot = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": self._EMAIL},
        )
        assert forgot.json().get("reset_token") is None

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": known_token, "new_password": "NewSecurePass9!"},
        )
        assert resp.status_code == 204

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": self._EMAIL, "password": "NewSecurePass9!"},
        )
        assert login.status_code == 200

    async def test_reset_password_invalid_token_returns_400(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "notarealtoken", "new_password": "NewSecurePass9!"},
        )
        assert resp.status_code == 400

    async def test_reset_password_token_used_twice_returns_400(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        known_token = "test-fixed-reset-token-9876543210"
        monkeypatch.setattr(
            "app.routers.auth.secrets.token_urlsafe", lambda *_: known_token
        )

        await self._register(client)
        await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": self._EMAIL},
        )

        await client.post(
            "/api/v1/auth/reset-password",
            json={"token": known_token, "new_password": "NewSecurePass9!"},
        )
        second = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": known_token, "new_password": "AnotherPass9!"},
        )
        assert second.status_code == 400
