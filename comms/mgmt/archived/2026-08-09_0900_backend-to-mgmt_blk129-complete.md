# BLK-129: Async Run Execution — Implementation Complete

## Summary

BLK-129 is fully implemented and tested. All 1166 tests pass (14 integration tests deselected, 0 failures).

## What Was Delivered

### 1. RunExecutor (`src/api/run_executor.py`)
- Bounded async worker pool (default 3 workers, configurable via `max_concurrent_runs`)
- Per-run `RunContext` with SSE emitter, cooperative `RunControl`, and event buffer
- Queue-based dispatch with `asyncio.Queue`
- State persistence on every status transition
- `get_executor()` singleton with `reset_executor()` for testing

### 2. POST /runs — Async Enqueue (`src/api/routes/runs.py`)
- Returns **202 Accepted** with `queued` status and run ID immediately
- Returns **429** with `Retry-After` header when worker pool is full
- Auto-routing and budget checks still run synchronously before enqueue

### 3. Live SSE Streaming (`src/api/routes/runs.py`)
- **Live mode**: subscribes to per-run emitter for active runs (queued/running/paused)
- **Late-subscriber buffer**: replayed buffered events before live stream
- **Replay mode**: stored events for completed/failed/cancelled runs
- **`run_id` in complete event**: `emit_complete()` now accepts optional `run_id` param

### 4. Cooperative Pause/Resume/Stop (`src/api/routes/runs.py`, `src/agent/graph.py`)
- `RunControl` flags checked at ReAct cycle boundaries (`should_act`, `should_continue`)
- Pause: sets `pause_requested` → agent terminates at next boundary with `PAUSED` status
- Resume: clears pause, sets `resume_event`
- Stop: sets `cancel_requested` → agent terminates with `CANCELLED` status
- `RunStatus.CANCELLED` added to state and graph conditional edges
- Endpoints return **202** when action taken, **200** for no-ops

### 5. GET /admin/queue (`src/api/main.py`)
- Returns queue depth, active worker count, max workers, and run list

### 6. Orphan Recovery + Graceful Shutdown (`src/api/run_executor.py`, `src/api/main.py`)
- `recover_orphans()`: marks interrupted runs (running/paused/queued) as `failed` on boot
- Startup hook: starts executor + recovers orphans
- Shutdown hook: drains workers gracefully via sentinel-based queue shutdown

### 7. Progressive field_update + gate_triggered Events (`src/agent/graph.py`)
- `observe_node` emits `field_update` events as fields are grounded (with bbox, confidence, risk_tier)
- `reflect_node` emits `progress` and `trajectory_warning`/`trajectory_critical` events
- `plan_node` emits `thought` events
- `act_node` emits `tool_call` and `tool_result` events
- `terminate_node` emits `complete` event with run_id

## Files Modified

- `src/api/run_executor.py` — **NEW**: RunExecutor, RunControl, RunContext
- `src/api/run_engine.py` — Added `execute_run_async`, refactored to `_execute_run_impl`
- `src/api/routes/runs.py` — Async enqueue, live SSE, cooperative control endpoints
- `src/api/sse.py` — `emit_complete` now accepts `run_id`
- `src/api/main.py` — Admin queue endpoint, startup/shutdown hooks
- `src/agent/graph.py` — Emitter wiring in all nodes, control checks in edges, `CANCELLED` status
- `src/agent/state.py` — `RunStatus.CANCELLED`
- `src/config.py` — `max_concurrent_runs` setting
- `src/tests/test_async_runs.py` — **NEW**: 40 tests covering all BLK-129 features
- `src/tests/test_agent_control.py` — Updated for new status codes
- `src/tests/test_e2e.py` — Updated mock `build_react_graph` signatures

## Test Results

- **1166 passed**, 14 deselected (integration), 0 failures
- 40 new BLK-129 tests covering: RunControl, RunContext, RunExecutor enqueue/pause/resume/cancel,
  orphan recovery, queue status, API 202/429 responses, admin/queue endpoint, graph CANCELLED edges,
  SSE complete with run_id, executor lifecycle, late-subscriber buffer
