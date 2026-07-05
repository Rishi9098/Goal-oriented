"""
Simple in-memory token-bucket rate limiter.

Each unique IP is tracked in a dict; buckets refill continuously at
`requests / window_seconds` tokens per second.

This is intentionally lightweight (no Redis dependency) so the rate limiter
works out of the box.  For multi-process deployments, replace the in-memory
store with Redis and a Lua INCR script.
"""

import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Routes that are extra sensitive — apply the rate limit even if the general
# limit is not yet reached.
_SENSITIVE_PREFIXES = ("/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/simulate")


class _TokenBucket:
    __slots__ = ("tokens", "last_refill")

    def __init__(self, capacity: float) -> None:
        self.tokens: float = capacity
        self.last_refill: float = time.monotonic()

    def consume(self, capacity: float, rate: float) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(capacity, self.tokens + elapsed * rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._capacity = float(settings.rate_limit_requests)
        self._rate = self._capacity / settings.rate_limit_window_seconds
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(self._capacity)
        )
        self._lock = Lock()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: object) -> Response:
        path = request.url.path
        is_sensitive = any(path.startswith(p) for p in _SENSITIVE_PREFIXES)

        # Health check and docs bypass rate limiting
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)  # type: ignore[misc]

        ip = self._get_client_ip(request)
        key = f"{ip}:{path}" if is_sensitive else ip

        with self._lock:
            bucket = self._buckets[key]
            allowed = bucket.consume(self._capacity, self._rate)

        if not allowed:
            logger.warning("rate_limit_exceeded ip=%s path=%s", ip, path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )

        return await call_next(request)  # type: ignore[misc]
