"""
Simple in-memory token-bucket rate limiter.

Each unique IP is tracked in a dict; buckets refill continuously at
`requests / window_seconds` tokens per second.

This is intentionally lightweight (no Redis dependency) so the rate limiter
works out of the box.  For multi-process deployments, replace the in-memory
store with Redis and a Lua INCR script.
"""

import time
from collections import OrderedDict
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

# How often (in seconds) to sweep TTL-expired buckets, as a fraction of the
# configured TTL. Amortizes the O(n) sweep instead of running it every request.
_CLEANUP_INTERVAL_FRACTION = 0.5


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
        self._bucket_ttl = float(settings.rate_limit_bucket_ttl_seconds)
        self._max_buckets = settings.rate_limit_max_buckets
        self._trusted_proxies = frozenset(settings.trusted_proxy_ips)
        # OrderedDict gives O(1) "move to end on access" + "pop oldest",
        # which is all an LRU eviction policy needs.
        self._buckets: OrderedDict[str, _TokenBucket] = OrderedDict()
        self._lock = Lock()
        self._last_cleanup = time.monotonic()

    def _get_client_ip(self, request: Request) -> str:
        direct_ip = request.client.host if request.client else "unknown"

        # Only honor X-Forwarded-For when the direct TCP peer is a known,
        # trusted reverse proxy/load balancer. Otherwise a client can set
        # this header to any value and get a fresh rate-limit bucket on
        # every request, bypassing the limiter entirely.
        if direct_ip not in self._trusted_proxies:
            return direct_ip

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return direct_ip

    def _evict_locked(self) -> None:
        """Must be called while holding self._lock."""
        now = time.monotonic()

        if now - self._last_cleanup >= self._bucket_ttl * _CLEANUP_INTERVAL_FRACTION:
            stale_cutoff = now - self._bucket_ttl
            stale_keys = [
                key for key, bucket in self._buckets.items() if bucket.last_refill < stale_cutoff
            ]
            for key in stale_keys:
                del self._buckets[key]
            self._last_cleanup = now

        while len(self._buckets) > self._max_buckets:
            self._buckets.popitem(last=False)

    async def dispatch(self, request: Request, call_next: object) -> Response:
        path = request.url.path
        is_sensitive = any(path.startswith(p) for p in _SENSITIVE_PREFIXES)

        # Health check and docs bypass rate limiting
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)  # type: ignore[misc]

        ip = self._get_client_ip(request)
        key = f"{ip}:{path}" if is_sensitive else ip

        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _TokenBucket(self._capacity)
                self._buckets[key] = bucket
            else:
                self._buckets.move_to_end(key)
            allowed = bucket.consume(self._capacity, self._rate)
            self._evict_locked()

        if not allowed:
            logger.warning("rate_limit_exceeded ip=%s path=%s", ip, path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )

        return await call_next(request)  # type: ignore[misc]
