from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "Northstar API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"

    # Database
    database_url: str = "postgresql+asyncpg://northstar:northstar@localhost:5432/northstar"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Refresh token is delivered as an httpOnly cookie rather than in the
    # response body (see AUDIT.md #4). secure/samesite relax automatically
    # in debug mode so local HTTP dev still works.
    refresh_cookie_name: str = "ns_refresh_token"
    csrf_cookie_name: str = "ns_csrf_token"
    cookie_domain: str | None = None

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # AI / Copilot
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Monte Carlo
    monte_carlo_simulations: int = 10_000
    monte_carlo_seed: int | None = None

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_bucket_ttl_seconds: int = 600
    rate_limit_max_buckets: int = 50_000
    # IPs of reverse proxies/load balancers allowed to set X-Forwarded-For.
    # Empty by default: X-Forwarded-For is ignored and the direct TCP peer
    # is used, since an untrusted client can set this header to any value.
    trusted_proxy_ips: list[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
