---
id: BLK-165
title: "Persist cost, tokens, and timestamps in serialized run records"
status: assigned
priority: high
estimate: S
assigned_to: backend
created: 2026-08-09T00:25:00+05:30
by: mgmt
depends_on: []
---

## Problem

`serialize_extraction_result()` in `src/api/run_engine.py:179-213`
omits cost, token, and timestamp data from the persisted run record.
The analytics dashboard (BLK-119) needs these fields for the Cost
per Day and Processing Time Distribution charts.

### Current serialized shape

```python
{
    "id": run_id,
    "definition_id": definition_id,
    "document_url": document_path,
    "status": ...,
    "current_cycle": result.total_cycles,
    "total_fields": result.gap_report.total_fields,
    "extracted_fields_count": len(result.gap_report.satisfied),
    "fields": [...],
}
```

### Missing fields

1. **`total_cost_usd`** — available in `result.token_usage_summary["total_cost_usd"]`
   but not included in the serialized output.

2. **`total_tokens`** — available in `result.token_usage_summary["total_tokens"]`
   but not included.

3. **`created_at`** — set in the initial `store.save_run()` call in
   `run_executor.py:222-232` but **overwritten** when
   `run_engine.py:457` calls `store.save_run()` with the serialized
   result (which doesn't include `created_at`).

4. **`started_at`** — set by `_persist_run()` in
   `run_executor.py:401` but overwritten by the same `save_run()`.

5. **`completed_at`** — set by `_persist_run()` in
   `run_executor.py:402` but overwritten by the same `save_run()`.

## Fix

### 1. Extend `serialize_extraction_result`

Add to the returned dict:

```python
"total_cost_usd": result.token_usage_summary.get("total_cost_usd", 0.0),
"total_tokens": result.token_usage_summary.get("total_tokens", 0),
"created_at": ...,  # from state or pass-through
"started_at": ...,  # from state or pass-through
"completed_at": ...,  # datetime.now(timezone.utc).isoformat()
```

For timestamps: either pass them through from the caller, or
read the existing run record from the store before overwriting
and preserve `created_at`/`started_at`.

### 2. Fix the overwrite bug

`run_engine.py:457` calls `store.save_run()` which does
`store.create("runs", run_id, data)` — this overwrites the
existing record. Change to `store.update_run()` (which does
`store.update("runs", run_id, data)`) to merge instead of
replace. Or ensure `serialize_extraction_result` includes all
fields that were in the initial record.

### 3. Ensure `_persist_run` in run_executor doesn't clobber

`_persist_run()` at `run_executor.py:388-407` reads the existing
record, updates it, and calls `store.update_run()`. This is
correct. But `run_engine.py:457` calls `store.save_run()` which
**creates** (overwrites). This is the bug.

**Recommended fix:** Change `run_engine.py:457` from
`store.save_run(run_id, serialized)` to
`store.update_run(run_id, serialized)`. This preserves fields
set by the executor (`created_at`, `started_at`) and merges
the serialized result.

## Acceptance Criteria

- [ ] `serialize_extraction_result` includes `total_cost_usd`,
      `total_tokens`, `completed_at`
- [ ] `created_at` and `started_at` preserved in final run record
      (not overwritten by `save_run`)
- [ ] `GET /runs` response items include these fields
- [ ] `GET /runs/{id}` response includes these fields
- [ ] Existing tests pass — no regression
- [ ] New test: verify cost/tokens/timestamps in serialized result
