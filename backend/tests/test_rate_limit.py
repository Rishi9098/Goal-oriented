"""Unit tests for the in-memory rate limiter's IP resolution and eviction logic."""

import time

from starlette.requests import Request

from app.middleware.rate_limit import RateLimitMiddleware, _TokenBucket


def _make_request(
    client_host: str, headers: dict[str, str] | None = None, path: str = "/api/v1/x"
) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


async def _dummy_app(scope: object, receive: object, send: object) -> None:  # pragma: no cover
    pass


def _make_middleware(**overrides: object) -> RateLimitMiddleware:
    mw = RateLimitMiddleware(_dummy_app)
    for key, value in overrides.items():
        setattr(mw, key, value)
    return mw


class TestClientIPResolution:
    def test_untrusted_client_xff_header_is_ignored(self) -> None:
        mw = _make_middleware(_trusted_proxies=frozenset())
        req = _make_request("203.0.113.5", {"X-Forwarded-For": "1.1.1.1"})
        assert mw._get_client_ip(req) == "203.0.113.5"

    def test_spoofed_xff_cannot_mint_a_new_identity_per_request(self) -> None:
        # This is the regression case for the bypass: an attacker who is not
        # coming through a trusted proxy must always resolve to the same key
        # regardless of what X-Forwarded-For claims.
        mw = _make_middleware(_trusted_proxies=frozenset())
        resolved_ips = {
            mw._get_client_ip(_make_request("203.0.113.5", {"X-Forwarded-For": f"1.1.1.{i}"}))
            for i in range(10)
        }
        assert resolved_ips == {"203.0.113.5"}

    def test_trusted_proxy_xff_header_is_honored(self) -> None:
        mw = _make_middleware(_trusted_proxies=frozenset({"10.0.0.1"}))
        req = _make_request("10.0.0.1", {"X-Forwarded-For": "198.51.100.9, 10.0.0.1"})
        assert mw._get_client_ip(req) == "198.51.100.9"

    def test_no_xff_header_falls_back_to_direct_peer(self) -> None:
        mw = _make_middleware(_trusted_proxies=frozenset({"10.0.0.1"}))
        req = _make_request("10.0.0.1")
        assert mw._get_client_ip(req) == "10.0.0.1"


class TestBucketEviction:
    def test_bucket_count_is_capped_via_lru_eviction(self) -> None:
        mw = _make_middleware(_max_buckets=3, _bucket_ttl=9_999.0)
        for i in range(10):
            with mw._lock:
                mw._buckets[f"ip-{i}"] = _TokenBucket(mw._capacity)
                mw._evict_locked()
        assert len(mw._buckets) <= 3
        # The most recently inserted keys should have survived the eviction.
        assert "ip-9" in mw._buckets
        assert "ip-0" not in mw._buckets

    def test_recently_accessed_bucket_is_not_evicted_first(self) -> None:
        mw = _make_middleware(_max_buckets=2, _bucket_ttl=9_999.0)
        with mw._lock:
            mw._buckets["old"] = _TokenBucket(mw._capacity)
            mw._buckets["recent"] = _TokenBucket(mw._capacity)
            mw._buckets.move_to_end("old")  # touch "old" most recently
            mw._buckets["new"] = _TokenBucket(mw._capacity)
            mw._evict_locked()
        assert "recent" not in mw._buckets
        assert "old" in mw._buckets
        assert "new" in mw._buckets

    def test_stale_buckets_are_swept_by_ttl(self) -> None:
        mw = _make_middleware(_bucket_ttl=1.0, _last_cleanup=0.0)
        with mw._lock:
            stale = _TokenBucket(mw._capacity)
            stale.last_refill = time.monotonic() - 10.0
            fresh = _TokenBucket(mw._capacity)
            mw._buckets["stale-ip"] = stale
            mw._buckets["fresh-ip"] = fresh
            mw._evict_locked()
        assert "stale-ip" not in mw._buckets
        assert "fresh-ip" in mw._buckets
