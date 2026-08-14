---
id: BLK-244
type: bug
title: "compact and rollback endpoints are no-ops that simulate success"
priority: high
status: backlog
phase: 2
owner: devin
created: 2026-08-09T12:20:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [backend, api, compact, rollback, control, false-success, reliability]
---

## Description

Two agent-control endpoints in `src/api/routes/runs.py` respond with success-like semantics while doing nothing meaningful:

1. **`compact_run`** (`/runs/{run_id}/compact`, lines ~509-541): if the run is not already complete it returns `{"compaction_triggered": True, "message": "Compaction requested — will trigger on next cycle."}`. But the route never writes any flag/field into the run record that the graph reads. The graph's compaction is driven by its own in-memory `_compact_requested` on the *live* LangGraph state/context — a separate object in the executor, not the persisted run JSON. So after returning, the next cycle will NOT be routed through the compact node; the run's auto-compaction threshold is unaffected.

2. **`rollback`** (`/runs/{run_id}/rollback`, lines ~659-701): only annotates the persisted run record with `rolled_back_from`/`rolled_back_to` metadata. It never restores a LangGraph state snapshot/checkpoint, and the run itself is already complete in the v1 synchronous model. The docstring is honest about the v1 limitation, but the outbound API says "rollback" and the frontend exposes it as a live control.

## Problem Statement

Both endpoints exist because the platform exposes live agent control (BLK-046) in the frontend. But against the current synchronous/v1 run model they cannot have the advertised effect. They return 200 with believable messages, so the frontend shows compact/rollback as "available", users click them, and nothing changes. In a live (non-blocked) run scenario, `compact_run` cannot reach the running context at all since the run executes in a worker with its own state.

This is part of the same "live control" gap as BLK-184 (pause/resume): the UI offers controls the runtime can't honor. It must be fixed with the async model + checkpointing work (BLK-129/BLK-036), not patched in isolation.

## Acceptance Criteria

- [ ] `compact` endpoint either (a) actually triggers compaction on a live run's context (via executor/SSE), or (b) returns a truthful `202`/`not-supported` with a clear message until live runs support it
- [ ] `rollback` endpoint accepts a real checkpoint, or is de-scoped/hidden from the UI until checkpoint-based rollback exists
- [ ] No endpoint returns 200 "success" for an action it did not perform
- [ ] Frontend control buttons are gated on actual capability (disable compact/rollback when run is terminal or not supported)
- [ ] Tests distinguish "request accepted" from "performed"

## Constraints

- Tie to BLK-184/BLK-224 completion; do not hack live-state mutation into the synchronous store alongside the running graph
- Keep the v1 path functionally intact; just stop lying about out-of-band effects

## Dependencies

- `src/api/routes/runs.py`
- `src/api/run_engine.py` / `run_executor.py` (context wiring)
- `src/agent/graph.py` compact node [BLK-039]
- `src/agent/state.py` checkpoint model [BLK-046/§]
- Related BLK-184, BLK-224

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T12:20 (mgmt)**: Filed after tracing both handlers — neither delivers a real effect to the live graph.
