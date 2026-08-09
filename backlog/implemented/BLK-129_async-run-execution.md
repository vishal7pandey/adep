---
id: BLK-129
type: feature
title: "Async run execution — background workers, live SSE, run cancellation"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: XL
depends-on: []
tags: [backend, architecture, async, sse, concurrency, blocks-batch]
---

## Problem

Runs execute **synchronously** inside the HTTP request. This is the
root cause of several separate symptoms we've been treating
individually:

1. **BLK-090** (deferred): SSE "streams" are a replay of an already
   finished trace, not live progress. The user watches a fake
   real-time feed of something that already happened.
2. **Agent control is theatre**: pause/resume/stop (BLK-046) cannot
   actually interrupt a synchronous run — by the time the control
   request arrives the run has finished.
3. **BLK-118** (batch processing) is impossible — batch means many
   concurrent runs.
4. **HTTP timeouts**: a 10-page document can exceed typical proxy
   timeouts. The client disconnects and loses the result.
5. **No concurrency**: one long run blocks the worker.

We keep deferring these as separate items. They are all one problem.

## Requirements

### 1. Run Executor

An async task executor owning run lifecycle:

- `POST /api/v1/runs` enqueues and returns `202 Accepted` immediately
  with the run id and status `queued`
- A bounded worker pool executes runs (default concurrency 3,
  configurable)
- Run state persists to `.adep/runs/{run_id}/` on every state
  transition so progress survives a restart
- Queue depth and worker utilisation exposed via
  `GET /api/v1/admin/queue`

v1: in-process `asyncio` task pool. Do **not** introduce Celery or
Redis yet — document that multi-process scaling is a follow-up.

### 2. Live SSE

The event stream must emit as the run progresses:

- Worker publishes events to a per-run `asyncio.Queue`
- SSE endpoint subscribes and forwards
- Late subscribers receive buffered history, then live events — so
  reconnect works without losing the earlier trace
- Heartbeat comment every 15 s to keep proxies from closing the
  connection
- Clean termination event on completion/failure/cancellation

This closes BLK-090 properly instead of documenting it as a limitation.

### 3. Real Agent Control

With a background worker, pause/resume/stop become genuine:

- **Pause**: worker checks a cooperative pause flag at each ReAct
  cycle boundary and blocks until resumed
- **Resume**: clears the flag
- **Stop**: sets a cancellation flag; the worker terminates at the
  next cycle boundary and returns partial results with an explicit
  `cancelled` status
- **Rollback**: unchanged semantics, but now applies to a live run

Cancellation must be **cooperative**, never a hard task kill — a
killed task leaves the trace and token accounting inconsistent.

### 4. Cleanup & Robustness

- Orphaned runs (worker died mid-run) detected on boot and marked
  `failed` with a clear reason, not left `running` forever
- SSE subscriber cleanup on disconnect so queues don't leak
- Graceful shutdown: stop accepting new runs, let in-flight runs
  finish or checkpoint, then exit

## Acceptance Criteria

- [ ] Run executor with a bounded async worker pool
- [ ] `POST /api/v1/runs` returns 202 with `queued` status
- [ ] Configurable concurrency (default 3)
- [ ] Run state persisted on every transition
- [ ] `GET /api/v1/admin/queue` reports depth and utilisation
- [ ] SSE emits live events as the run progresses
- [ ] Late subscribers get buffered history then live events
- [ ] SSE heartbeat every 15 s
- [ ] Pause actually blocks a running agent at a cycle boundary
- [ ] Resume actually continues it
- [ ] Stop returns partial results with `cancelled` status
- [ ] Cancellation is cooperative, never a hard kill
- [ ] Orphaned runs marked `failed` on boot with a reason
- [ ] SSE subscriber cleanup on disconnect (no queue leak)
- [ ] Graceful shutdown drains or checkpoints in-flight runs
- [ ] BLK-090 closed as genuinely fixed
- [ ] Tests: enqueue, concurrent runs, live SSE ordering, reconnect
      mid-run, pause/resume/stop, orphan recovery, graceful shutdown
- [ ] No regression in existing tests

## Constraints

- **No Celery/Redis in v1.** In-process asyncio only. Document the
  multi-process limitation explicitly.
- Frontend currently expects a synchronous-ish flow. This changes the
  run-start contract from `201 + result` to `202 + poll/stream`.
  **Send a contract proposal to mgmt before implementing** so
  frontend can adapt in the same cycle (PROTOCOL.md §7).
- Token accounting and trace integrity must remain correct across
  pause/resume and cancellation.

## Notes

This unblocks BLK-118 (batch processing) and properly closes BLK-090.
It is the highest-leverage architectural item after BLK-109.

Because it changes an API contract, follow the interface-contract
process in PROTOCOL.md §7: propose, get both teams to approve, then
implement.
