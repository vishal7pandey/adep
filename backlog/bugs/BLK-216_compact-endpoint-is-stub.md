---
id: BLK-216
type: bug
title: "Manual compact endpoint is a stub — returns 200 but does nothing for active runs"
priority: low
status: backlog
phase: 2
owner: devin
created: 2026-08-09T13:00:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [api, runs, compaction, stub, agent-control]
---

## Description

The `POST /runs/{run_id}/compact` endpoint in `src/api/routes/runs.py:509-541` is a stub for completed runs and a no-op for active runs.

For completed/failed runs, it returns:
```json
{
    "run_id": "...",
    "compaction_triggered": false,
    "message": "Run has already completed. Manual compaction is only meaningful during live execution."
}
```

For active runs, it returns:
```json
{
    "run_id": "...",
    "compaction_triggered": true,
    "message": "Compaction requested — will trigger on next cycle."
}
```

But the endpoint never actually sets `_compact_requested=True` on the run state, never signals the executor, and never interacts with the LangGraph state. The message says "will trigger on next cycle" but nothing is communicated to the running agent.

## Problem Statement

- The endpoint claims compaction was triggered but doesn't actually request it — the agent never sees the signal
- Auto-compaction at threshold works (implemented in `graph.py` `compact_node`), but manual compaction via API is a no-op
- The frontend `compactRun` function exists and calls this endpoint, giving users false control
- BLK-039 (trace compaction) is marked as implemented, but the manual trigger path is broken

## Acceptance Criteria

- [ ] For active runs: signal the executor to set `_compact_requested=True` on the run's agent state, similar to how `pause_run` signals the executor
- [ ] For completed runs: the current behavior (informative message) is acceptable
- [ ] Add a test that verifies the compact signal reaches the agent state

## Constraints

- Auto-compaction already works — this is only about the manual trigger path
- Coordinate with the executor's cooperative control mechanism (same pattern as pause/resume/stop)

## Dependencies

- `src/api/routes/runs.py:509-541`
- `src/api/run_executor.py` (executor cooperative control)
- `frontend/lib/api.ts` (`compactRun` function)

## Notes

- Found during full-repo audit; related to BLK-215 (rollback stub) — same pattern of stub endpoints under "agent control"

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
