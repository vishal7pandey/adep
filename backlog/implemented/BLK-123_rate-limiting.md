---
id: BLK-123
type: feature
title: "Rate limiting middleware — per-key and per-IP request throttling"
priority: medium
status: backlog
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: [BLK-122]
tags: [backend, security, rate-limiting, abuse-prevention]
---

## Problem

No rate limiting exists. The OpenAPI spec advertises `429` but that
is only emitted by budget enforcement (BLK-051), not by request
throttling.

A caller can hammer `POST /api/v1/runs` and:
- Exhaust the daily LLM budget in seconds
- Saturate the synchronous run executor
- Fill the disk with document uploads

## Requirements

### Token Bucket Per Key / Per IP

- Authenticated requests: bucket keyed by `key_id`
- Unauthenticated requests (when auth disabled): bucket keyed by
  client IP
- In-memory implementation for v1 (single process). Document that
  multi-process deployments need Redis — that's a v2 concern.

### Tiered Limits

| Endpoint class | Default limit |
|----------------|---------------|
| `POST /runs` | 10 / minute |
| `POST /documents` | 20 / minute |
| Mutating (`POST`/`PUT`/`DELETE`) | 60 / minute |
| Read (`GET`) | 300 / minute |
| SSE streams | 5 concurrent per key |

All configurable via `src/config.py` settings.

### Response Headers

On every response:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset` (unix timestamp)

On 429:
- `Retry-After` (seconds)
- Body: `{"detail": {"error": "rate_limit_exceeded", "retry_after": N}}`

### Concurrent SSE Cap

Track open SSE connections per key. Reject new streams beyond the cap
with 429. Release the slot on disconnect (including abnormal
disconnect).

## Acceptance Criteria

- [ ] Token bucket limiter with per-key and per-IP keying
- [ ] Tiered limits per endpoint class, all config-driven
- [ ] `X-RateLimit-*` headers on all responses
- [ ] `Retry-After` header on 429
- [ ] Concurrent SSE connection cap with correct slot release
- [ ] Config flag `ADE_RATE_LIMIT_ENABLED` (default: false for tests)
- [ ] Health/ready endpoints exempt
- [ ] Tests: limit enforcement, header correctness, bucket refill,
      SSE cap, slot release on disconnect
- [ ] No regression in existing tests

## Constraints

- Disabled by default so the existing test suite is unaffected
- Must not leak memory — evict idle buckets on a timer
- Do not use a heavyweight dependency; a small in-house token bucket
  is preferred over adding `slowapi` unless there's a clear win
