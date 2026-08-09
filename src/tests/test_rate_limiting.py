"""Tests for BLK-123: Rate limiting middleware.

Covers:
- Token bucket: consume, refill, retry_after calculation
- Tiered limits: POST /runs, POST /documents, mutating, GET
- Per-key vs per-IP bucket keying
- X-RateLimit-* headers on responses
- 429 with Retry-After header and body
- Concurrent SSE cap: acquire, reject, release
- Idle bucket eviction
- Health/ready endpoints exempt
- Disabled by default (no headers when disabled)
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.rate_limit import (
    RateLimiter,
    TokenBucket,
    get_limiter,
    reset_limiter,
    install_rate_limit_middleware,
)


# ---------------------------------------------------------------------------
# TokenBucket unit tests
# ---------------------------------------------------------------------------

class TestTokenBucket:
    """Token bucket core logic [BLK-123]."""

    def test_new_bucket_starts_full(self):
        bucket = TokenBucket(capacity=10)
        assert bucket.tokens == 10.0

    def test_consume_succeeds_when_tokens_available(self):
        bucket = TokenBucket(capacity=10)
        allowed, retry_after = bucket.consume(1)
        assert allowed is True
        assert retry_after == 0.0
        assert bucket.tokens == 9.0

    def test_consume_fails_when_empty(self):
        bucket = TokenBucket(capacity=2)
        bucket.consume(2)  # drain
        allowed, retry_after = bucket.consume(1)
        assert allowed is False
        assert retry_after > 0

    def test_bucket_refills_over_time(self):
        bucket = TokenBucket(capacity=10, refill_period_seconds=60)
        bucket.consume(10)  # drain completely
        assert bucket.tokens < 1
        # Simulate time passing
        bucket.last_refill -= 30  # 30 seconds passed
        bucket._refill()
        assert bucket.tokens > 4  # should have ~5 tokens
        assert bucket.tokens < 6

    def test_bucket_refill_capped_at_capacity(self):
        bucket = TokenBucket(capacity=5)
        bucket.consume(5)
        bucket.last_refill -= 9999  # huge time gap
        bucket._refill()
        assert bucket.tokens == 5.0

    def test_reset_time_returns_timestamp(self):
        bucket = TokenBucket(capacity=10)
        bucket.consume(5)
        reset = bucket.reset_time()
        assert reset > time.time()
        assert isinstance(reset, float)


# ---------------------------------------------------------------------------
# RateLimiter unit tests
# ---------------------------------------------------------------------------

def _make_request(method: str = "GET", path: str = "/api/v1/runs",
                  api_key=None, client_ip: str = "127.0.0.1") -> MagicMock:
    """Create a mock Request for rate limiting tests."""
    request = MagicMock(spec=Request)
    request.method = method
    request.url.path = path
    request.client = MagicMock()
    request.client.host = client_ip
    if api_key is not None:
        request.state.api_key = api_key
    else:
        # Remove api_key attribute to simulate unauthenticated
        if hasattr(request.state, "api_key"):
            delattr(request.state, "api_key")
    return request


class TestRateLimiter:
    """RateLimiter logic [BLK-123]."""

    def test_check_allows_request_under_limit(self):
        limiter = reset_limiter()
        request = _make_request("GET", "/api/v1/runs")
        result = asyncio.run(limiter.check(request))
        assert result is None  # allowed

    def test_check_blocks_request_over_limit(self):
        limiter = reset_limiter()
        request = _make_request("POST", "/api/v1/runs")
        # Exhaust the bucket (10 requests for POST /runs)
        for _ in range(10):
            asyncio.run(limiter.check(request))
        # 11th request should be blocked
        result = asyncio.run(limiter.check(request))
        assert result is not None
        assert result["allowed"] is False
        assert "retry_after" in result
        assert "limit" in result
        assert "remaining" in result
        assert "reset" in result

    def test_tier_post_runs(self):
        limiter = reset_limiter()
        request = _make_request("POST", "/api/v1/runs")
        tier = limiter._tier_for("POST", "/api/v1/runs")
        assert tier == "post_runs"

    def test_tier_post_documents(self):
        limiter = reset_limiter()
        tier = limiter._tier_for("POST", "/api/v1/documents")
        assert tier == "post_documents"

    def test_tier_mutating(self):
        limiter = reset_limiter()
        tier = limiter._tier_for("PUT", "/api/v1/definitions/def-1")
        assert tier == "mutating"

    def test_tier_get(self):
        limiter = reset_limiter()
        tier = limiter._tier_for("GET", "/api/v1/runs")
        assert tier == "get"

    def test_bucket_key_uses_key_id_when_authenticated(self):
        limiter = reset_limiter()
        api_key = MagicMock()
        api_key.key_id = "adep_test123"
        request = _make_request(api_key=api_key)
        key = limiter._bucket_key(request)
        assert key == "key:adep_test123"

    def test_bucket_key_uses_ip_when_unauthenticated(self):
        limiter = reset_limiter()
        request = _make_request(client_ip="192.168.1.1")
        key = limiter._bucket_key(request)
        assert key == "ip:192.168.1.1"

    def test_exempt_paths_not_limited(self):
        limiter = reset_limiter()
        request = _make_request("GET", "/health")
        result = asyncio.run(limiter.check(request))
        assert result is None

    def test_exempt_openapi_not_limited(self):
        limiter = reset_limiter()
        request = _make_request("GET", "/openapi.json")
        result = asyncio.run(limiter.check(request))
        assert result is None

    def test_different_tiers_have_independent_buckets(self):
        limiter = reset_limiter()
        # Exhaust POST /runs tier
        post_request = _make_request("POST", "/api/v1/runs")
        for _ in range(10):
            asyncio.run(limiter.check(post_request))
        # GET should still be allowed (different tier)
        get_request = _make_request("GET", "/api/v1/runs")
        result = asyncio.run(limiter.check(get_request))
        assert result is None

    def test_different_keys_have_independent_buckets(self):
        limiter = reset_limiter()
        # Key 1 exhausts POST /runs
        key1 = MagicMock()
        key1.key_id = "key1"
        req1 = _make_request("POST", "/api/v1/runs", api_key=key1)
        for _ in range(10):
            asyncio.run(limiter.check(req1))
        assert asyncio.run(limiter.check(req1)) is not None

        # Key 2 should still be allowed
        key2 = MagicMock()
        key2.key_id = "key2"
        req2 = _make_request("POST", "/api/v1/runs", api_key=key2)
        result = asyncio.run(limiter.check(req2))
        assert result is None


# ---------------------------------------------------------------------------
# SSE concurrency cap tests
# ---------------------------------------------------------------------------

class TestSSEConcurrency:
    """Concurrent SSE cap with slot release [BLK-123]."""

    def test_acquire_sse_slot_succeeds(self):
        limiter = reset_limiter()
        request = _make_request("GET", "/api/v1/runs/run-1/stream")
        acquired = asyncio.run(limiter.acquire_sse_slot(request))
        assert acquired is True

    def test_acquire_sse_slot_rejects_at_cap(self):
        limiter = reset_limiter()
        request = _make_request("GET", "/api/v1/runs/run-1/stream")
        # Acquire 5 slots (default cap)
        for _ in range(5):
            asyncio.run(limiter.acquire_sse_slot(request))
        # 6th should be rejected
        acquired = asyncio.run(limiter.acquire_sse_slot(request))
        assert acquired is False

    def test_release_sse_slot_allows_new_connection(self):
        limiter = reset_limiter()
        request = _make_request("GET", "/api/v1/runs/run-1/stream")
        # Fill up
        for _ in range(5):
            asyncio.run(limiter.acquire_sse_slot(request))
        # Release one
        asyncio.run(limiter.release_sse_slot(request))
        # Should be able to acquire again
        acquired = asyncio.run(limiter.acquire_sse_slot(request))
        assert acquired is True

    def test_release_below_zero_clamped(self):
        limiter = reset_limiter()
        request = _make_request("GET", "/api/v1/runs/run-1/stream")
        # Release without acquiring — should not go negative
        asyncio.run(limiter.release_sse_slot(request))
        # Should still be able to acquire
        acquired = asyncio.run(limiter.acquire_sse_slot(request))
        assert acquired is True

    def test_sse_slots_are_per_key(self):
        limiter = reset_limiter()
        key1 = MagicMock()
        key1.key_id = "key1"
        key2 = MagicMock()
        key2.key_id = "key2"
        req1 = _make_request("GET", "/api/v1/runs/run-1/stream", api_key=key1)
        req2 = _make_request("GET", "/api/v1/runs/run-1/stream", api_key=key2)

        # Key 1 fills up
        for _ in range(5):
            asyncio.run(limiter.acquire_sse_slot(req1))
        assert asyncio.run(limiter.acquire_sse_slot(req1)) is False

        # Key 2 should still be allowed
        assert asyncio.run(limiter.acquire_sse_slot(req2)) is True


# ---------------------------------------------------------------------------
# Idle bucket eviction tests
# ---------------------------------------------------------------------------

class TestBucketEviction:
    """Idle bucket eviction [BLK-123]."""

    def test_evict_removes_full_buckets(self):
        limiter = reset_limiter()
        # Create a bucket by making a request
        request = _make_request("GET", "/api/v1/runs")
        asyncio.run(limiter.check(request))
        assert len(limiter._buckets) > 0

        # Age the bucket so it fully refills (becomes idle)
        for bucket in limiter._buckets.values():
            bucket.last_refill -= 9999

        # Force eviction by setting last_eviction in the past
        limiter._last_eviction -= 9999  # way past eviction interval
        evicted = asyncio.run(limiter.evict_idle())
        assert evicted > 0
        assert len(limiter._buckets) == 0

    def test_evict_skips_recently_used_buckets(self):
        limiter = reset_limiter()
        request = _make_request("GET", "/api/v1/runs")
        # Make request to create bucket, then consume a token
        asyncio.run(limiter.check(request))
        bucket_id = list(limiter._buckets.keys())[0]
        limiter._buckets[bucket_id].tokens = 5.0  # partially used

        # Try to evict — partially used bucket should NOT be evicted
        limiter._last_eviction -= 9999
        evicted = asyncio.run(limiter.evict_idle())
        assert evicted == 0  # bucket has tokens < capacity, not idle

    def test_eviction_interval_respected(self):
        limiter = reset_limiter()
        # Recent eviction — should not evict
        evicted = asyncio.run(limiter.evict_idle())
        assert evicted == 0


# ---------------------------------------------------------------------------
# Integration tests with FastAPI
# ---------------------------------------------------------------------------

class TestRateLimitMiddleware:
    """Integration: rate limiting middleware with FastAPI [BLK-123]."""

    def _create_app(self, enabled: bool = True) -> FastAPI:
        """Create a test app with rate limiting enabled."""
        from src.config import settings
        original = settings.rate_limit_enabled
        settings.rate_limit_enabled = enabled

        app = FastAPI()

        @app.get("/api/v1/runs")
        async def list_runs():
            return {"items": []}

        @app.post("/api/v1/runs")
        async def start_run():
            return {"id": "run-1", "status": "queued"}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        install_rate_limit_middleware(app)

        settings.rate_limit_enabled = original
        return app

    def test_disabled_middleware_no_headers(self):
        app = self._create_app(enabled=False)
        reset_limiter()
        client = TestClient(app)
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" not in resp.headers

    def test_enabled_middleware_adds_headers(self):
        app = self._create_app(enabled=True)
        reset_limiter()
        client = TestClient(app)
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers

    def test_429_on_limit_exceeded(self):
        app = self._create_app(enabled=True)
        reset_limiter()
        client = TestClient(app)
        # POST /runs has limit 10/min
        for _ in range(10):
            resp = client.post("/api/v1/runs")
            assert resp.status_code == 200

        # 11th should be 429
        resp = client.post("/api/v1/runs")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        data = resp.json()
        assert data["detail"]["error"] == "rate_limit_exceeded"
        assert "retry_after" in data["detail"]

    def test_health_endpoint_exempt(self):
        app = self._create_app(enabled=True)
        reset_limiter()
        client = TestClient(app)
        # Health should not have rate limit headers
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" not in resp.headers

    def test_429_includes_rate_limit_headers(self):
        app = self._create_app(enabled=True)
        reset_limiter()
        client = TestClient(app)
        for _ in range(10):
            client.post("/api/v1/runs")
        resp = client.post("/api/v1/runs")
        assert resp.status_code == 429
        assert resp.headers.get("X-RateLimit-Limit") is not None
        assert resp.headers.get("Retry-After") is not None


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestRateLimitConfig:
    """Config settings [BLK-123]."""

    def test_rate_limit_disabled_by_default(self):
        from src.config import Settings
        s = Settings()
        assert s.rate_limit_enabled is False

    def test_tier_limits_have_defaults(self):
        from src.config import Settings
        s = Settings()
        assert s.rate_limit_post_runs_per_min == 10
        assert s.rate_limit_post_documents_per_min == 20
        assert s.rate_limit_mutating_per_min == 60
        assert s.rate_limit_get_per_min == 300
        assert s.rate_limit_sse_concurrent_per_key == 5

    def test_eviction_interval_default(self):
        from src.config import Settings
        s = Settings()
        assert s.rate_limit_eviction_interval_seconds == 300
