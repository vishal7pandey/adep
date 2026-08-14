---
id: BLK-283
type: bug
title: "Rollback endpoint is a stub — records request but never restores state"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T12:55:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [api, runs, rollback, stub, dead-code, agent-control]
---

## Description

The `POST /runs/{run_id}/rollback` endpoint in `src/api/routes/runs.py:659-701` is a stub. Its own docstring admits:

> "In v1 (synchronous runs with in-memory checkpoints), this endpoint records the rollback request. Full checkpoint restoration requires async runs (v2)."

The endpoint writes `rolled_back_from` and `rolled_back_to` fields to the run data and sets status to `"rolled_back"`, but it does **not**:
- Restore the agent state to the target cycle
- Replay or undo trace entries
- Restore the extraction dict to its state at the target cycle
- Restore field_attempts or attempted sets
- Actually re-execute from the target cycle

The frontend has a `rollbackRun` API function (`frontend/lib/api.ts`) and the SSE types include `SSERolledBackEvent`, but the backend can't deliver on the promise.

## Problem Statement

- A user clicks "Rollback to Cycle N" in the UI, gets a 200 response saying "Rolled back from cycle X to N", but nothing actually happened — the run data is just annotated with metadata
- The run status becomes `"rolled_back"` which is not a valid `RunStatus` enum value in `src/agent/state.py` — the frontend doesn't know how to handle this status
- The `SSERolledBackEvent` type exists in the frontend but is never emitted by the backend
- This is listed under "Agent control endpoints [BLK-046]" which is marked as implemented in the backlog
- The rollback feature gives false confidence — users think they can undo agent mistakes but they can't

## Acceptance Criteria

- [ ] Either implement full rollback (requires LangGraph checkpoint persistence, state serialization, and re-execution from checkpoint) or remove the endpoint and frontend UI
- [ ] If implementing: persist LangGraph checkpoints per cycle, restore state on rollback, emit `SSERolledBackEvent`, re-execute from target cycle
- [ ] If removing: delete the endpoint, remove `rollbackRun` from `frontend/lib/api.ts`, remove `SSERolledBackEvent` from `frontend/lib/sse.ts`, update BLK-046
- [ ] If deferring: change the endpoint to return 501 Not Implemented with a clear message, and disable the rollback button in the frontend

## Constraints

- Full rollback requires persistent LangGraph checkpoints, which is a significant architectural change
- Don't leave a stub that pretends to work

## Dependencies

- `src/api/routes/runs.py:659-701`
- `frontend/lib/api.ts` (`rollbackRun` function)
- `frontend/lib/sse.ts` (`SSERolledBackEvent`)
- `backlog/implemented/features/BLK-046_agent-control.md`

## Notes

- Found during full-repo audit; the compact endpoint (BLK-216) has a similar stub pattern

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
