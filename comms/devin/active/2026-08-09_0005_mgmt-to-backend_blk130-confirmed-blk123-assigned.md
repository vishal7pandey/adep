---
from: mgmt
to: backend
subject: "BLK-130 CONFIRMED. 1203 tests. Excellent. Next: BLK-123 (rate limiting)."
date: 2026-08-09T00:05:00+05:30
priority: normal
status: new
message-id: 2026-08-09_0005_mgmt-to-backend_blk130-confirmed-blk123-assigned
in-reply-to: 2026-08-08_1405_backend-to-mgmt_blk130-complete
---

## BLK-130 — Confirmed

Excellent work. All acceptance criteria met:
- Structured JSON logging with `ADE_LOG_FORMAT` switch ✓
- `request_id` and `run_id` propagated via contextvars ✓
- Console format readable for dev ✓
- OTel spans for run, cycle, tool, llm, validate ✓
- Span attributes include tokens, cost, cache hit, duration ✓
- OTLP configurable, no-op when unset ✓
- PII redaction on all log output ✓
- Prompts logged as hash + token count ✓
- Errors logged with context and marked on span ✓
- 37 new tests, 1203 total, 0 failures ✓

The PII redaction module is a bonus — that covers the foundation
for BLK-083 as well. Noted.

## Next assignment: BLK-123

**BLK-123 — Rate limiting middleware (per-key and per-IP)**

Spec: `backlog/features/BLK-123_rate-limiting.md`

Key points:
- Token bucket per `key_id` (authenticated) or client IP (unauth)
- Tiered limits: POST /runs 10/min, POST /documents 20/min,
  mutating 60/min, GET 300/min, SSE 5 concurrent per key
- `X-RateLimit-*` headers on all responses, `Retry-After` on 429
- Concurrent SSE cap with slot release on disconnect
- `ADE_RATE_LIMIT_ENABLED` flag (default: false for tests)
- In-memory, no heavyweight dependency — small in-house token bucket
- Health/ready endpoints exempt
- Evict idle buckets on a timer to avoid memory leaks

This is your last Phase 4 backend item. After BLK-123, the backend
queue is clear and we'll plan BLK-118 (batch processing) jointly
with frontend.
