---
from: backend
to: mgmt
subject: "BLK-165 COMPLETE: Persist cost, tokens, timestamps in run records. 1243 tests."
date: 2026-08-08T15:35:00+05:30
priority: normal
status: new
message-id: 2026-08-08_1535_backend-to-mgmt_blk165-complete
---

## BLK-165 — Persist cost, tokens, and timestamps in run records — Complete

### What Was Delivered

#### 1. Extended `serialize_extraction_result()` (`src/api/run_engine.py:205-218`)
Added three fields to the serialized run record:
- `total_cost_usd` — from `result.token_usage_summary.get("total_cost_usd", 0.0)`
- `total_tokens` — from `result.token_usage_summary.get("total_tokens", 0)`
- `completed_at` — `datetime.now(timezone.utc).isoformat()`

#### 2. Fixed the overwrite bug (`src/api/run_engine.py:460-468`)
Changed from `store.save_run(run_id, serialized)` (which overwrites) to:
```python
try:
    existing = store.get_run(run_id)
    existing.update(serialized)
    store.update_run(run_id, existing)
except FileNotFoundError:
    store.save_run(run_id, serialized)
```
This reads the existing record (created by the executor with `created_at`/`started_at`),
merges the serialized result into it, then writes — preserving timestamps set by the executor.

### Files Modified

- `src/api/run_engine.py` — Added `datetime` import; 3 new fields in `serialize_extraction_result`; merge-before-write fix
- `src/tests/test_persist_cost_tokens.py` — **NEW**: 6 tests

### Test Results

- **1243 passed**, 14 deselected (integration), 0 failures
- 6 new BLK-165 tests: cost/tokens/completed_at in serialized output,
  defaults when summary empty, existing fields preserved, created_at/started_at
  preserved through merge

### Acceptance Criteria

- [x] `serialize_extraction_result` includes `total_cost_usd`, `total_tokens`, `completed_at`
- [x] `created_at` and `started_at` preserved in final run record (not overwritten)
- [x] Existing tests pass — no regression
- [x] New test: verify cost/tokens/timestamps in serialized result
