# BLK-171: Zero-token runs with zero extracted fields complete as "completed" instead of "failed"

- **Priority:** P1 — High
- **Status:** implemented
- **Owner:** unassigned
- **Phase:** 5
- **Type:** bug
- **Reported:** 2026-08-08
- **Resolved:** 2026-08-09

## Resolution

Verified against current code (2026-08-09): `terminate_node` in `src/agent/graph.py` explicitly checks `total_tokens == 0 and not extraction` and forces `RunStatus.ERROR`; `map_status_to_frontend()` does not match `ERROR` in its `completed` branch so it falls through to `"failed"`. Moved from `backlog/bugs/` to `backlog/implemented/`; see BLK-192 for the process gap that let this sit unmoved. Note: the fix does not yet fail fast when the provider is simply unconfigured before a run starts — that gap is now tracked separately by BLK-173 and BLK-178.

## Problem

A run against a P&ID image using the "Advertising Insertion Order" definition completed with:
- 0 tokens used
- $0.0000 cost
- 0/6 fields grounded (0%)
- Status: "Completed"

This is misleading. A run that makes zero LLM calls and extracts zero fields is a failure, not a completion. The user sees "Completed" in the UI and may believe the extraction succeeded.

## Root Cause

The `terminate_node` in `agent/graph.py` sets status to `COMPLETE` or `PARTIAL` based on field coverage, but when zero fields are extracted and zero cycles run, the status logic doesn't explicitly flag this as a failure. The `map_status_to_frontend()` in `run_engine.py` maps `COMPLETE` and `PARTIAL` both to `"completed"`.

Additionally, the run executor may short-circuit when the LLM provider is not configured (empty API key) without setting an error status.

## Files Affected

- `src/agent/graph.py` — `terminate_node` status determination
- `src/api/run_engine.py` — `map_status_to_frontend()`
- `src/api/run_executor.py` — `_start_run`, `_execute_run` error handling

## Fix

1. In `terminate_node`: if zero fields were extracted AND zero LLM cycles ran, set status to `FAILED` with an error message
2. In `map_status_to_frontend`: consider mapping zero-field partial results to `"failed"` instead of `"completed"`
3. In `_start_run` / `_execute_run`: if the LLM provider is not configured (empty API key/endpoint), fail fast with a clear error message instead of silently completing
4. In the frontend: show a clear failure indicator when 0/6 fields are grounded

## Acceptance Criteria

- [ ] Runs with 0 extracted fields and 0 tokens report status "failed"
- [ ] Error message explains why (e.g., "No LLM provider configured" or "Agent could not extract any fields")
- [ ] Frontend shows failure state, not success state
- [ ] Runs with partial extraction (>0 fields) still report "completed" correctly
