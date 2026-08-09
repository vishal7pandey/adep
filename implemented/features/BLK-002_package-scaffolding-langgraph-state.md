---
id: BLK-002
type: feature
title: "Scaffold package layout & LangGraph State + node skeletons"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-001]
tags: [agent, state, scaffolding, foundation]
---

## Description

Scaffold the full package layout per vision.md §11 and implement the
LangGraph `State` TypedDict with all required keys. Create node skeletons
(plan, act, observe, reflect, terminate) as stub functions. **State stores
image handles, not pixels (§2.7)** — get this right before any tool is wired.

## Acceptance Criteria

- [ ] Package layout matches vision.md §11
- [ ] `AgentState` TypedDict with all keys (partial extraction, trace, gaps, cycles, status)
- [ ] `TraceEntry` and `DocumentHandle` dataclasses
- [ ] `compact_trace` function with rolling window + resolved-field pruning
- [ ] Node stubs: plan, act, observe, reflect, terminate
- [ ] State carries paths/IDs, never base64 blobs
- [ ] Unit tests for trace compaction

## Constraints

- State must carry image handles, not pixels (§2.7) — critical for scaling
- LangGraph typed State object
- Python 3.10+ type hints [TH]

## Dependencies

- BLK-001 (ToolResult, Grounding types needed in State)

## Notes

- vision.md §2.7, §10 Phase 1 step 2, §12.3 (trace compaction)
- Existing `src/agent/state.py` has a first draft — review and finalize
- Existing tests in `src/tests/test_state.py` should pass after refinement
