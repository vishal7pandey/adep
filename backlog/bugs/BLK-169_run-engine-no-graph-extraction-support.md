# BLK-169: Run engine does not handle graph_extraction task type

- **Priority:** P0 — Critical
- **Status:** backlog
- **Owner:** unassigned
- **Phase:** 5
- **Type:** bug
- **Reported:** 2026-08-08

## Problem

The `AgentDefinition` model has a `task_type` field (default "extraction", supports "graph_extraction"), and prebuilt definitions `def-pid-to-dexpi` and `def-pnid-to-dexpi` set `task_type: "graph_extraction"`. However, the run engine completely ignores this field:

1. `serialize_extraction_result()` in `run_engine.py` only serializes `FieldExtractionResult.field_values` — it has no code path for `GraphExtractionResult` (graph, node_grounding, edge_grounding, serialized_output).

2. The ReAct agent graph in `agent/graph.py` is wired for field extraction only. The `terminate_node` builds an `ExtractedResult` from field values, not a `GraphExtractionResult`.

3. The graph tools (detect_symbols, classify_symbol, detect_connections, trace_line, read_tag, build_graph, validate_topology, serialize_graph) exist and are implemented in `src/tools/graph/`, but the run engine doesn't register them in the tool registry for graph_extraction definitions.

4. The P&ID skill (`src/skills/pid_diagram.py`) exists with a proper system prompt and probe order, but is never wired into the run engine's skill registry.

## Root Cause

The graph extraction abstraction (§20 in vision.md) was implemented at the data model level (OutputContract, RunResult hierarchy, GraphExtractionResult) but was never wired into the run execution pipeline. The run engine still operates exclusively on the field extraction path.

## Files Affected

- `src/api/run_engine.py` — `serialize_extraction_result()`, `execute_run_impl()`, skill/template resolution
- `src/agent/graph.py` — `terminate_node` only builds `ExtractedResult`
- `src/templates/base.py` — `GraphExtractionResult` exists but is never populated
- `src/skills/pid_diagram.py` — skill exists but not in `_SKILL_REGISTRY`

## Fix

1. Register graph tools (detect_symbols, classify_symbol, etc.) in the tool registry
2. Register PnIDSkill in the skill registry
3. Add task_type dispatch in `execute_run_impl()` — when task_type is "graph_extraction", use graph extraction tools and build a `GraphExtractionResult` instead of `ExtractedResult`
4. Extend `serialize_extraction_result()` to handle `GraphExtractionResult` — serialize graph nodes/edges, serialized_output, topology validation results
5. Extend `terminate_node` in `agent/graph.py` to build `GraphExtractionResult` when task_type is graph_extraction
6. Include `task_type` in the serialized run result so the frontend can render appropriately

## Acceptance Criteria

- [ ] Running `def-pid-to-dexpi` on a P&ID image invokes graph extraction tools (detect_symbols, etc.)
- [ ] Run result includes graph nodes, edges, serialized_output (DEXPI XML, Smart P&ID JSON, GraphML)
- [ ] Run result includes `task_type: "graph_extraction"` field
- [ ] Topology validation results are included in run output
- [ ] All existing field extraction tests still pass
- [ ] Graph extraction produces real data from the document, not fabricated output
