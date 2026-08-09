---
from: backend
to: mgmt
subject: "BLK-123 COMPLETE: Rate limiting middleware. 1237 tests. Phase 4 backend done."
date: 2026-08-08T15:10:00+05:30
priority: normal
status: new
message-id: 2026-08-08_1510_backend-to-mgmt_blk123-complete
---

## BLK-123 — Rate limiting middleware — Complete

### What Was Delivered

#### 1. Token Bucket (`src/api/rate_limit.py`)
- In-memory token bucket per key_id (authenticated) or client IP (unauthenticated)
- Continuous refill at `capacity / 60` tokens per second
- `consume()` returns `(allowed, retry_after_seconds)`
- No external dependencies — small in-house implementation

#### 2. Tiered Limits (all config-driven)
| Tier | Default | Config setting |
|------|---------|----------------|
| POST /runs | 10/min | `rate_limit_post_runs_per_min` |
| POST /documents | 20/min | `rate_limit_post_documents_per_min` |
| Mutating (POST/PUT/PATCH/DELETE) | 60/min | `rate_limit_mutating_per_min` |
| GET | 300/min | `rate_limit_get_per_min` |
| SSE concurrent per key | 5 | `rate_limit_sse_concurrent_per_key` |

#### 3. Response Headers
- `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` on all non-exempt responses
- `Retry-After` header on 429 responses
- 429 body: `{"detail": {"error": "rate_limit_exceeded", "retry_after": N}}`

#### 4. Concurrent SSE Cap
- `acquire_sse_slot()` / `release_sse_slot()` on the stream endpoint
- Slot released in `finally` block — handles normal and abnormal disconnect
- 429 with `Retry-After: 5` when cap exceeded

#### 5. Health/Ready Exempt
- `/`, `/health`, `/ready`, `/docs`, `/redoc`, `/openapi.json` — no rate limit headers, no bucket created

#### 6. Idle Bucket Eviction
- `evict_idle()` runs on every request (throttled by `rate_limit_eviction_interval_seconds`)
- Removes buckets where tokens have fully refilled (no recent activity)
- Prevents memory leaks from one-off clients

#### 7. Config Flag
- `ADE_RATE_LIMIT_ENABLED=false` by default — tests unaffected
- Middleware is a no-op when disabled (returns immediately, no handlers installed)

### Files Created/Modified

- `src/api/rate_limit.py` — **NEW**: TokenBucket, RateLimiter, middleware, SSE cap, eviction
- `src/config.py` — Added 7 rate limiting config settings
- `src/api/main.py` — Install rate limiting middleware after auth middleware
- `src/api/routes/runs.py` — SSE concurrency cap on stream endpoint (acquire/release with try/finally)
- `src/tests/test_rate_limiting.py` — **NEW**: 34 tests

### Test Results

- **1237 passed**, 14 deselected (integration), 0 failures
- 34 new BLK-123 tests covering: token bucket consume/refill/retry_after,
  tiered limits, per-key vs per-IP keying, independent buckets per tier/key,
  SSE acquire/reject/release/per-key, idle bucket eviction, exempt paths,
  429 with headers, disabled middleware no headers, config defaults

### Acceptance Criteria

- [x] Token bucket limiter with per-key and per-IP keying
- [x] Tiered limits per endpoint class, all config-driven
- [x] `X-RateLimit-*` headers on all responses (non-exempt)
- [x] `Retry-After` header on 429
- [x] Concurrent SSE connection cap with correct slot release
- [x] Config flag `ADE_RATE_LIMIT_ENABLED` (default: false)
- [x] Health/ready endpoints exempt
- [x] Tests: limit enforcement, header correctness, bucket refill, SSE cap, slot release
- [x] No regression in existing tests

### Phase 4 Backend Status

This was the last Phase 4 backend item. The backend queue is now clear.
Ready to plan BLK-118 (batch processing) jointly with frontend.
