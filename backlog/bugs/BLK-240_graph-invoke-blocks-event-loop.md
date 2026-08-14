---
id: BLK-240
type: bug
title: "graph.invoke() blocks the entire asyncio event loop despite docstring claiming asyncio.to_thread"
priority: critical
status: backlog
phase: 1
owner: devin
created: 2026-08-09T12:00:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [backend, async, perf, reliability, run-executor, event-loop, critical]
---

## Description

`_execute_run_inner` (coroutine) in `src/api/run_engine.py` calls the synchronous `graph.invoke(...)` (line ~710) directly. It is reached from `src/api/run_executor.py:_execute_run` (line ~361 `await execute_run_async(...)`). `_execute_run`'s docstring claims:

> "The LangGraph invoke is synchronous, so we run it in a thread via asyncio.to_thread()."

No `asyncio.to_thread` (or any `run_in_executor`/thread) exists anywhere in the call chain — the docstring describes a design that was never implemented.

## Problem Statement

LangGraph `invoke` runs the LLM planner + tools on the calling thread for up to `settings.max_cycles_per_document` (30) steps. Because it runs directly inside the running event loop:

- Every HTTP endpoint freezes during a run — SSE `stream`/live feed, pause/cancel/approve, health, admin — nothing gets serviced while a run is executing.
- The N "workers" in `_worker_loop` (run_executor.py:326) do not run concurrently; they serialize behind the single blocked thread, so a slow 30-cycle run starves all queued runs.
- Cooperative control requests (pause/resume/stop) cannot even be received, compounding `BLK-184`.
- SSE events are appended to buffers but never flushed while the loop is blocked (workbench appears frozen).

## Acceptance Criteria

- [ ] `graph.invoke` executes on a worker thread (e.g. `await asyncio.to_thread(graph.invoke, state, config)`), never on the event loop
- [ ] A slow run no longer blocks health checks or unrelated API endpoints
- [ ] Multiple concurrent runs make progress (not strictly serial)
- [ ] Pause/cancel/approve requests are serviced during a run
- [ ] Regression test: start a run with a mock LLM that sleeps per-cycle and assert `GET /health` + a trivial route respond within a small timeout while the run executes; assert a second run starts while the first is in progress
- [ ] Update `_execute_run` docstring to match the real threading model (or remove the misleading claim)

## Constraints

- Do not break live SSE ordering/emit semantics; the emitter must still be callable from the worker thread
- Shared mutable run state (control flags, store) must remain thread-safe or be marshalled across the thread boundary explicitly
- Preserve recursion_limit config injection

## Dependencies

- `src/api/run_engine.py::_execute_run_inner`
- `src/api/run_executor.py::_execute_run` (docstring) and `_worker_loop`
- Related BLK-129 (async run execution) — this closes the remaining sync-per-run gap
- Related BLK-184 (pause/resume) — this bug is the reason pause cannot be serviced during a run

## Notes

- Discovery: full-repo audit + backtrace from `graph.invoke` (run_engine) to `await execute_run_async` (run_executor) — zero `to_thread`/`run_in_executor`/`anyio` present.
- The "3 workers" architecture does not deliver concurrency while this bug is live.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T12:00 (mgmt)**: Filed from audit backtrace; root cause is a missing thread boundary between the async API layer and the synchronous LangGraph call.
