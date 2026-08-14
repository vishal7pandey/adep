---
id: BLK-218
type: bug
title: "Graph extraction runtime does not use graph-specific validation or control metrics during the live loop"
priority: critical
status: backlog
phase: 1
owner: devin
created: 2026-08-09T11:10:00+05:30
started: null
completed: null
estimate: L
depends-on: []
tags: [agent, graph-extraction, validator, pid, runtime, wiring, critical]
---

## Description

The repo has a real graph task model:

- `GraphExtractionContract`
- `GraphExtractionResult`
- `TaskValidator._validate_graph()`
- a P&ID skill and graph toolchain

But the live ReAct loop does not use the graph validator during planning/reflect/termination fallback. It continues to run the flat-field extraction validator against the template class, even when `task_type == "graph_extraction"`.

## Problem Statement

Verified live-path mismatches:

- `src/agent/graph.py:reflect_node()` always calls `validate_extraction(...)`
- `src/api/run_engine.py` fallback result construction also calls `validate_extraction(...)` if `result` is missing
- `src/run.py` does the same in its fallback path
- `TaskValidator` exists in `src/agent/validator.py` but is not wired into the actual run loop

This has concrete consequences for graph tasks:

- continuation/termination decisions are based on flat required fields instead of graph completeness
- progress metrics use `_required_fields(template_schema)`, which is meaningless for graph contracts
- the graph-specific gap taxonomy (`NODE_MISSING`, `EDGE_MISSING`, `TOPOLOGY_VIOLATION`, `SERIALIZATION_FAILED`) is not what drives the loop
- the live agent can claim graph-task support while its core control logic still thinks in flat-field extraction terms

In other words, graph extraction currently has specialized tools and a specialized result type, but not a specialized runtime control loop.

## Acceptance Criteria

- [ ] Live graph-extraction runs use `TaskValidator` or equivalent graph-aware validation during reflect/continue decisions
- [ ] Progress counts and completion criteria for graph tasks are graph-aware rather than `_required_fields()` based
- [ ] `execute_run()` and `run()` fallback result construction use the same task-aware validation path as the graph
- [ ] Integration tests cover a graph-extraction run where continuation is driven by graph gaps, not flat fields
- [ ] The runtime clearly separates extraction-task and graph-task orchestration logic where they differ materially

## Constraints

- Keep field-extraction behavior stable while fixing graph-task routing
- Avoid duplicating validator logic across `graph.py`, `run_engine.py`, and `run.py`
- Preserve the current serialized frontend contract for graph outputs where possible

## Dependencies

- `src/agent/graph.py`
- `src/agent/validator.py`
- `src/api/run_engine.py`
- `src/run.py`
- `src/templates/base.py`
- `src/templates/pid_diagram.py`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
