"""Rate limiting middleware — token bucket per key/IP [BLK-123].

Provides:
- Token bucket limiter with per-key (authenticated) or per-IP (unauth) keying
- Tiered limits: POST /runs 10/min, POST /documents 20/min, mutating 60/min, GET 300/min
- X-RateLimit-* headers on all responses, Retry-After on 429
- Concurrent SSE cap with slot release on disconnect
- Idle bucket eviction on a timer to avoid memory leaks
- Health/ready endpoints exempt
- Enabled by default (ADE_RATE_LIMIT_ENABLED=true); set false for local dev/tests [SCRUM-63]

In-memory implementation for v1 (single process). Multi-process deployments
need Redis — that's a v2 concern.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import settings

logger = logging.getLogger(__name__)

# Paths exempt from rate limiting
EXEMPT_PATHS = {
    "/",
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/openapi.json",
    "/api/v1/health",
    "/api/v1/locales",
}


# ---------------------------------------------------------------------------
# Token Bucket
# ---------------------------------------------------------------------------


@dataclass
class TokenBucket:
    """In-memory token bucket for rate limiting [BLK-123].

    Tokens refill at a rate of `capacity / refill_period_seconds` per second.
    """

    capacity: int
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.monotonic)
    refill_period_seconds: int = 60  # tokens refill fully over this period

    def __post_init__(self) -> None:
        if self.tokens == 0.0:
            self.tokens = float(self.capacity)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        refill_rate = self.capacity / self.refill_period_seconds
        self.tokens = min(self.capacity, self.tokens + elapsed * refill_rate)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> tuple[bool, float]:
        """Try to consume tokens. Returns (allowed, retry_after_seconds)."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        # Calculate retry-after: time until enough tokens refill
        needed = tokens - self.tokens
        refill_rate = self.capacity / self.refill_period_seconds
        retry_after = needed / refill_rate if refill_rate > 0 else 1.0
        return False, max(1.0, retry_after)

    def reset_time(self) -> float:
        """Return unix timestamp when the bucket will be fully refilled."""
        self._refill()
        if self.tokens >= self.capacity:
            return time.time()
        refill_rate = self.capacity / self.refill_period_seconds
        needed = self.capacity - self.tokens
        return time.time() + (needed / refill_rate if refill_rate > 0 else 0)


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """Manages token buckets per key and SSE concurrency tracking [BLK-123]."""

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._sse_connections: dict[str, int] = {}
        self._last_eviction: float = time.monotonic()
        self._lock = asyncio.Lock()

    def _bucket_key(self, request: Request) -> str:
        """Determine the bucket key: key_id for authenticated, IP for unauth."""
        api_key = getattr(request.state, "api_key", None)
        if api_key is not None:
            return f"key:{api_key.key_id}"
        # Fall back to client IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _tier_for(self, method: str, path: str) -> str:
        """Determine the rate limit tier for a request [BLK-123]."""
        if method == "POST" and path.startswith("/api/v1/runs"):
            return "post_runs"
        if method == "POST" and path.startswith("/api/v1/documents"):
            return "post_documents"
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            return "mutating"
        return "get"

    def _capacity_for_tier(self, tier: str) -> int:
        """Get the bucket capacity (requests per minute) for a tier."""
        return {
            "post_runs": settings.rate_limit_post_runs_per_min,
            "post_documents": settings.rate_limit_post_documents_per_min,
            "mutating": settings.rate_limit_mutating_per_min,
            "get": settings.rate_limit_get_per_min,
        }.get(tier, settings.rate_limit_get_per_min)

    def _bucket_id(self, key: str, tier: str) -> str:
        """Composite bucket ID: key + tier."""
        return f"{key}:{tier}"

    async def check(self, request: Request) -> dict[str, Any] | None:
        """Check rate limit for a request.

        Returns None if allowed, or a dict with rate limit info for 429 response.
        Also sets X-RateLimit-* header values via the returned dict.
        """
        path = request.url.path
        if path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return None

        key = self._bucket_key(request)
        tier = self._tier_for(request.method, path)
        capacity = self._capacity_for_tier(tier)
        bucket_id = self._bucket_id(key, tier)

        async with self._lock:
            bucket = self._buckets.get(bucket_id)
            if bucket is None or bucket.capacity != capacity:
                bucket = TokenBucket(capacity=capacity)
                self._buckets[bucket_id] = bucket

            allowed, retry_after = bucket.consume(1)
            remaining = int(bucket.tokens)
            reset = bucket.reset_time()

        result = {
            "allowed": allowed,
            "limit": capacity,
            "remaining": remaining,
            "reset": int(reset),
        }

        if not allowed:
            result["retry_after"] = int(retry_after) + 1  # round up
            return result

        return None  # allowed — no 429 needed

    async def acquire_sse_slot(self, request: Request) -> bool:
        """Try to acquire an SSE concurrency slot. Returns True if allowed."""
        key = self._bucket_key(request)
        async with self._lock:
            current = self._sse_connections.get(key, 0)
            if current >= settings.rate_limit_sse_concurrent_per_key:
                return False
            self._sse_connections[key] = current + 1
            logger.debug("SSE slot acquired for %s (active: %d)", key, current + 1)
            return True

    async def release_sse_slot(self, request: Request) -> None:
        """Release an SSE concurrency slot on disconnect."""
        key = self._bucket_key(request)
        async with self._lock:
            current = self._sse_connections.get(key, 0)
            if current > 0:
                self._sse_connections[key] = current - 1
                if self._sse_connections[key] == 0:
                    del self._sse_connections[key]
                logger.debug("SSE slot released for %s (active: %d)", key, current - 1)

    async def evict_idle(self) -> int:
        """Evict idle buckets that haven't been used recently. Returns count evicted."""
        now = time.monotonic()
        if now - self._last_eviction < settings.rate_limit_eviction_interval_seconds:
            return 0

        self._last_eviction = now
        # A bucket is idle if its tokens are fully refilled (no recent consumption)
        evicted = 0
        async with self._lock:
            to_remove = []
            for bucket_id, bucket in self._buckets.items():
                bucket._refill()
                if bucket.tokens >= bucket.capacity:
                    to_remove.append(bucket_id)
            for bucket_id in to_remove:
                del self._buckets[bucket_id]
                evicted += 1

        if evicted > 0:
            logger.debug("Evicted %d idle rate limit buckets", evicted)
        return evicted

    def get_stats(self) -> dict[str, Any]:
        """Return current stats for admin/queue endpoint."""
        return {
            "buckets": len(self._buckets),
            "sse_connections": dict(self._sse_connections),
        }

    def reset(self) -> None:
        """Reset all state (for testing)."""
        self._buckets.clear()
        self._sse_connections.clear()
        self._last_eviction = time.monotonic()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    """Get the singleton RateLimiter instance."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def reset_limiter() -> RateLimiter:
    """Reset the singleton limiter (for testing)."""
    global _limiter
    if _limiter is not None:
        _limiter.reset()
    else:
        _limiter = RateLimiter()
    return _limiter


# ---------------------------------------------------------------------------
# Middleware installation
# ---------------------------------------------------------------------------


def install_rate_limit_middleware(app: FastAPI) -> None:
    """Install rate limiting middleware on the FastAPI app [BLK-123].

    Only active when settings.rate_limit_enabled is True.
    """
    if not settings.rate_limit_enabled:
        return

    limiter = get_limiter()

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        path = request.url.path

        # Skip exempt paths entirely [BLK-123]
        if path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Check rate limit
        result = await limiter.check(request)

        if result is not None:
            # Rate limited — return 429
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "error": "rate_limit_exceeded",
                        "retry_after": result["retry_after"],
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(result["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result["reset"]),
                    "Retry-After": str(result["retry_after"]),
                },
            )

        # Not rate limited — proceed and add headers to response
        response = await call_next(request)

        # Add rate limit headers to non-exempt responses
        if result is None:
            # We need to get the bucket info for headers
            key = limiter._bucket_key(request)
            tier = limiter._tier_for(request.method, request.url.path)
            capacity = limiter._capacity_for_tier(tier)
            bucket_id = limiter._bucket_id(key, tier)
            bucket = limiter._buckets.get(bucket_id)
            if bucket is not None:
                bucket._refill()
                response.headers["X-RateLimit-Limit"] = str(capacity)
                response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
                response.headers["X-RateLimit-Reset"] = str(int(bucket.reset_time()))
            else:
                response.headers["X-RateLimit-Limit"] = str(capacity)
                response.headers["X-RateLimit-Remaining"] = str(capacity)
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))

        # Periodically evict idle buckets
        await limiter.evict_idle()

        return response
