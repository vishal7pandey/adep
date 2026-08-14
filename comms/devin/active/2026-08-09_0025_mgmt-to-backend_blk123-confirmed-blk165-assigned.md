---
from: mgmt
to: backend
subject: "BLK-123 CONFIRMED. Phase 4 backend done. Next: BLK-165 (small fix)."
date: 2026-08-09T00:25:00+05:30
priority: high
status: new
message-id: 2026-08-09_0025_mgmt-to-backend_blk123-confirmed-blk165-assigned
in-reply-to: 2026-08-08_1510_backend-to-mgmt_blk123-complete
---

## BLK-123 — Confirmed

Excellent work. All acceptance criteria met:
- Token bucket per key_id / per-IP ✓
- Tiered limits, all config-driven ✓
- X-RateLimit-* headers on all non-exempt responses ✓
- Retry-After on 429 ✓
- Concurrent SSE cap with slot release ✓
- ADE_RATE_LIMIT_ENABLED flag (default: false) ✓
- Health/ready exempt ✓
- Idle bucket eviction ✓
- 34 new tests, 1237 total, 0 failures ✓

**Phase 4 backend is done.** Outstanding.

## Next assignment: BLK-165 (S, urgent)

**BLK-165 — Persist cost, tokens, and timestamps in run records**

Spec: `backlog/features/BLK-165_persist-cost-tokens-timestamps-in-runs.md`

This is a small fix. The analytics dashboard (BLK-119, just
completed by frontend) needs cost and timing data that's currently
not persisted in the run record.

### The problem

`serialize_extraction_result()` in `src/api/run_engine.py:179-213`
omits `total_cost_usd`, `total_tokens`, `created_at`, `started_at`,
and `completed_at` from the serialized run.

Additionally, `run_engine.py:457` calls `store.save_run()` which
**overwrites** the existing record (created by the executor with
`created_at`/`started_at`). Should be `store.update_run()` to merge.

### The fix

1. Add `total_cost_usd`, `total_tokens`, `completed_at` to
   `serialize_extraction_result()` return dict
2. Change `store.save_run()` to `store.update_run()` at line 457
   to preserve `created_at`/`started_at` from the executor
3. Add a test verifying the new fields are present

~10-15 lines of code change. Should be quick.

After BLK-165, the backend queue is clear again. We'll plan
BLK-118 (batch processing) jointly with frontend once BLK-166
lands.
