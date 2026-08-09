---
id: BLK-008
type: feature
title: "ReAct graph implementation (LangGraph nodes + edges)"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-002, BLK-003]
tags: [agent, react, langgraph, core]
---

## Description

Implement the full ReAct loop as a LangGraph state machine with nodes
(plan, act, observe, reflect, terminate) and conditional edges. The `plan`
node takes the GapReport + skill hints and decides the next action. The
`act` node calls one tool. The `observe` node processes the result. The
`reflect` node runs the Outcome Validator. The `terminate` node returns
the ExtractedResult.

## Acceptance Criteria

- [ ] LangGraph graph with 5 nodes: plan, act, observe, reflect, terminate
- [ ] Conditional edges: reflect → plan (gaps remain) or → terminate (done/exhausted)
- [ ] LLM integration via Azure GPT-5.4 for the plan node
- [ ] Tool calls dispatched through ToolRegistry
- [ ] Tool errors handled as structured ToolResult(ok=False) in observe node (§2.7)
- [ ] Per-region `attempted` set in State to prevent amnesiac retries (§12.3)
- [ ] State correctly updated at each node (handles, not pixels)
- [ ] Trace entries logged at each cycle (including failures)
- [ ] Integration test with mocked LLM + mocked tools
- [ ] Integration test: provider failure → agent switches modality or terminates with gaps

## Constraints

- LangGraph for graph structure (locked decision §9)
- GPT-5.4 via Azure for LLM calls
- State carries image handles, not base64 (§2.7)

## Dependencies

- BLK-002 (State + node skeletons)
- BLK-003 (ToolRegistry)
- BLK-009 (Outcome Validator — reflect node uses it)

## Notes

- vision.md §2.2 (ReAct loop), §4 (architecture), §9 (LangGraph decision)
- This is the core of the engine — the largest single item in Phase 1
