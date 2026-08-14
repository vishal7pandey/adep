---
id: BLK-270
type: bug
title: "Pause/resume lifecycle is not actually resumable and store state drifts from executor state"
priority: critical
status: backlog
phase: 1
owner: devin
created: 2026-08-09T10:10:00+05:30
started: null
completed: null
estimate: L
depends-on: []
tags: [backend, async, control, pause, resume, sse, state-machine, critical]
---

## Description

The async control model presents pause/resume as a cooperative lifecycle, but the current implementation terminates the graph on pause instead of suspending it. The route layer also updates persisted run status optimistically, which can diverge from the in-memory executor context.

## Problem Statement

There are two coupled defects:

- `src/agent/graph.py` sets `RunStatus.PAUSED` and routes to `"terminate"` when `control.pause_requested` is seen
- `src/api/run_executor.py` documents `resume_event` as a wait primitive, but nothing actually waits on it

So a paused run does not suspend and later continue; it exits.

At the same time:

- `src/api/routes/runs.py` writes `"paused"` and `"running"` directly into the store via `_update_run_status()`
- `src/api/run_executor.py` only allows `resume_run()` when the live `RunContext.status` is exactly `"paused"`

This creates a mismatch where:

- the store can say `"paused"` before the worker context is paused
- the API can report resume success semantics while the executor rejects the request
- the frontend can believe a run is resumable even though the graph already terminated

## Acceptance Criteria

- [ ] Pause semantics suspend execution rather than terminating the run
- [ ] Resume semantics continue the same run from a valid paused state
- [ ] Route responses reflect executor truth instead of only persisted store state
- [ ] Store status and in-memory executor status stay synchronized across pause/resume/cancel transitions
- [ ] SSE emits distinct paused/resumed/complete states that match the actual lifecycle
- [ ] Tests cover pause-then-resume on a real execution path, not only store mutation

## Constraints

- Preserve cooperative cancellation at graph cycle boundaries
- Avoid introducing hard task kills or unsafe thread interruption
- Keep replay behavior for completed runs intact

## Dependencies

- Likely touches `src/api/run_executor.py`, `src/api/routes/runs.py`, `src/agent/graph.py`, and SSE tests
- Related to async run execution work in `BLK-129`, but not fixed by that ticket’s current implementation

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
