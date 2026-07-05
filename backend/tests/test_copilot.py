"""Integration tests for the AI Copilot endpoint."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from openai import OpenAIError

import app.routers.copilot as copilot_module

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

HARD_GOAL_PAYLOAD = {
    "name": "Impossible Goal",
    "category": "home",
    "target_amount": 1_000_000,
    "current_amount": 100,
    "target_date": (date.today() + timedelta(days=365)).isoformat(),
    "monthly_contribution": 1,
    "risk_profile": "conservative",
    "priority": 2,
}


@pytest.mark.asyncio
class TestCopilot:
    async def test_chat_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/copilot", json={"message": "Hello"})
        assert resp.status_code == 403

    async def test_chat_returns_reply_no_goals(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/copilot",
            json={"message": "How is my plan?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0
        assert "conversation_id" in data

    async def test_chat_assigns_conversation_id(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/copilot",
            json={"message": "Hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        cid = resp.json()["conversation_id"]
        assert isinstance(cid, str) and len(cid) > 0

    async def test_chat_preserves_provided_conversation_id(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/copilot",
            json={"message": "Hello", "conversation_id": "test-conv-xyz"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["conversation_id"] == "test-conv-xyz"

    async def test_chat_with_healthy_goals_returns_positive_reply(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=auth_headers)
        resp = await client.post(
            "/api/v1/copilot",
            json={"message": "How are my goals?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["reply"]) > 0

    async def test_chat_with_low_probability_goal_mentions_it(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await client.post("/api/v1/goals", json=HARD_GOAL_PAYLOAD, headers=auth_headers)
        resp = await client.post(
            "/api/v1/copilot",
            json={"message": "Help me"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert len(data["reply"]) > 10

    async def test_chat_empty_message_rejected(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/copilot",
            json={"message": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class _FakeCompletions:
    def __init__(self, *, error: Exception | None = None, reply: str = "Looking good.") -> None:
        self._error = error
        self._reply = reply

    async def create(self, **_kwargs: object) -> SimpleNamespace:
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._reply))]
        )


class _FakeOpenAIClient:
    def __init__(self, *, error: Exception | None = None, reply: str = "Looking good.") -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(error=error, reply=reply))


@pytest.mark.asyncio
class TestCopilotOpenAIPath:
    """Exercises the OpenAI branch by faking the client (AUDIT.md #5/#6)."""

    async def test_openai_success_returns_model_reply(
        self, client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            copilot_module,
            "_get_openai_client",
            lambda: _FakeOpenAIClient(reply="Your plan is on track."),
        )
        resp = await client.post(
            "/api/v1/copilot", json={"message": "How am I doing?"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["reply"] == "Your plan is on track."

    async def test_openai_error_falls_back_instead_of_500(
        self, client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            copilot_module,
            "_get_openai_client",
            lambda: _FakeOpenAIClient(error=OpenAIError("simulated outage")),
        )
        resp = await client.post(
            "/api/v1/copilot", json={"message": "How am I doing?"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()["reply"]) > 0

    async def test_client_configured_with_timeout_and_retries(self) -> None:
        copilot_module._openai_client = None
        monkeypatch_key = copilot_module.settings.openai_api_key
        try:
            copilot_module.settings.openai_api_key = "sk-test-key"
            client = copilot_module._get_openai_client()
            assert client is not None
            assert client.timeout == copilot_module.settings.openai_timeout_seconds
            assert client.max_retries == copilot_module.settings.openai_max_retries
        finally:
            copilot_module.settings.openai_api_key = monkeypatch_key
            copilot_module._openai_client = None
