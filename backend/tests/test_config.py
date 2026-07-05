"""Regression tests for Settings env-var parsing edge cases."""

import pytest

from app.config import Settings


class TestBlankEnvVarsMeanUnset:
    """MONTE_CARLO_SEED= and COOKIE_DOMAIN= in .env.example are meant to mean
    "unset", but pydantic tries int("") for the former unless blank strings
    are explicitly coerced to None first."""

    def test_blank_monte_carlo_seed_parses_as_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        monkeypatch.setenv("MONTE_CARLO_SEED", "")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.monte_carlo_seed is None

    def test_blank_cookie_domain_parses_as_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        monkeypatch.setenv("COOKIE_DOMAIN", "")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cookie_domain is None

    def test_non_blank_monte_carlo_seed_still_parses_as_int(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        monkeypatch.setenv("MONTE_CARLO_SEED", "42")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.monte_carlo_seed == 42

    def test_blank_openai_api_key_stays_empty_string_not_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # openai_api_key is `str`, not `str | None` — it intentionally uses ""
        # to mean "disabled". The blank-to-None coercion must stay scoped to
        # monte_carlo_seed/cookie_domain only, or this field breaks validation.
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        monkeypatch.setenv("OPENAI_API_KEY", "")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.openai_api_key == ""
