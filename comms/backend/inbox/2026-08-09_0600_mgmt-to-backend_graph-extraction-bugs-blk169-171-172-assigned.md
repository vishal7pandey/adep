---
from: mgmt
to: backend
subject: "URGENT: Graph extraction bug cluster — BLK-169, BLK-171, BLK-172 assigned"
date: 2026-08-09T06:00:00+05:30
priority: high
status: new
message-id: 2026-08-09_0600_mgmt-to-backend_graph-extraction-bugs
---

## Context: Fabricated P&ID Extraction Output

During testing of `sample-pid-01.jpg`, a user ran the "Advertising
Insertion Order" definition on a P&ID diagram. The run produced
**0 tokens, $0.0000, 0/6 fields grounded** — yet the frontend displayed
fabricated DEXPI XML, Smart P&ID JSON, and GraphML output with fake
equipment tags (P-101A, V-204, PIT-301, T-102) that don't exist in the
drawing.

A full root cause analysis identified 6 bugs across frontend and
backend. Three are assigned to you. Two are P0 critical.

---

## BLK-169 — Run engine does not handle graph_extraction task type (P0)

**This is your top priority.**

The graph extraction abstraction was built at the data model level
(`OutputContract`, `RunResult` hierarchy, `GraphExtractionResult` in
`src/templates/base.py`) and the graph tools are fully implemented
in `src/tools/graph/` (detect_symbols, classify_symbol,
detect_connections, trace_line, read_tag, build_graph,
validate_topology, serialize_graph). The P&ID skill exists in
`src/skills/pid_diagram.py` with a correct system prompt and probe
order.

**But none of it is wired into the run execution pipeline.** The run
engine (`run_engine.py`) operates exclusively on the field extraction
path. `serialize_extraction_result()` only handles
`FieldExtractionResult.field_values`. The `terminate_node` in
`agent/graph.py` only builds `ExtractedResult`.

### What needs to happen:

1. Register graph tools in the tool registry so they're available
   when task_type is `graph_extraction`
2. Register `PnIDSkill` in `_SKILL_REGISTRY`
3. Add task_type dispatch in `execute_run_impl()` — when task_type
   is `graph_extraction`, use graph extraction tools and build a
   `GraphExtractionResult` instead of `ExtractedResult`
4. Extend `serialize_extraction_result()` to handle
   `GraphExtractionResult` — serialize graph nodes/edges,
   serialized_output (DEXPI XML, Smart P&ID JSON, GraphML), topology
   validation results
5. Extend `terminate_node` in `agent/graph.py` to build
   `GraphExtractionResult` when task_type is graph_extraction
6. Include `task_type` in the serialized run result so the frontend
   can render appropriately

### Key files:
- `src/api/run_engine.py` — serialization, skill/template resolution
- `src/agent/graph.py` — terminate_node
- `src/templates/base.py` — GraphExtractionResult (exists, unused)
- `src/skills/pid_diagram.py` — PnIDSkill (exists, unregistered)
- `src/tools/graph/__init__.py` — all graph tools (exist, unregistered)
- `src/definitions/prebuilt.py` — def-pnid-to-dexpi (exists, task_type set)

### Acceptance criteria:
- [ ] Running `def-pnid-to-dexpi` on a P&ID image invokes graph tools
- [ ] Run result includes graph nodes, edges, serialized_output
- [ ] Run result includes `task_type: "graph_extraction"` field
- [ ] Topology validation results included in run output
- [ ] All existing field extraction tests still pass
- [ ] Graph extraction produces real data from the document

Spec: `backlog/bugs/BLK-169_run-engine-no-graph-extraction-support.md`

---

## BLK-171 — Zero-token runs complete as "success" (P1)

A run with 0 tokens and 0 extracted fields reported status "Completed"
instead of "Failed". The LLM was likely never called (empty Azure API
key), but the run engine didn't fail fast.

### What needs to happen:

1. In `terminate_node`: if zero fields extracted AND zero LLM cycles
   ran, set status to `FAILED` with an error message
2. In `map_status_to_frontend()`: consider mapping zero-field partial
   results to `"failed"` instead of `"completed"`
3. In `_start_run` / `_execute_run`: if the LLM provider is not
   configured (empty API key/endpoint), fail fast with a clear error
   message instead of silently completing

### Key files:
- `src/agent/graph.py` — terminate_node status logic
- `src/api/run_engine.py` — map_status_to_frontend()
- `src/api/run_executor.py` — _start_run, _execute_run

Spec: `backlog/bugs/BLK-171_zero-token-runs-complete-as-success.md`

---

## BLK-172 — Duplicate P&ID definitions (P3, trivial)

Two identical definitions exist: `def-pid-to-dexpi` and
`def-pnid-to-dexpi` with the same name, skill, template, and config.
Remove `def-pid-to-dexpi`, keep `def-pnid-to-dexpi` as canonical.

### Key files:
- `src/definitions/prebuilt.py` — lines 385-421

Spec: `backlog/bugs/BLK-172_duplicate-pid-definitions.md`

---

## Priority Order

1. **BLK-169** (P0) — wire graph extraction end-to-end
2. **BLK-171** (P1) — fail fast on zero-token runs
3. **BLK-172** (P3) — delete duplicate definition

BLK-169 is the critical path. The frontend team is assigned BLK-167
and BLK-168 in parallel, but their work depends on BLK-169 producing
real graph data in run results. Please prioritize accordingly.

Note: BLK-170 (definition-document mismatch guardrail) is filed but
not yet assigned — it will be assigned after BLK-169 is complete.

---

## Phase 5 Context

These bugs were discovered during initial Phase 5 testing. The graph
extraction feature was implemented at the data model level during
Phase 4 (BLK-101 to BLK-103, BLK-110, BLK-111) but was never wired
end-to-end. This is the gap we're closing.

Your existing Phase 5 assignments (BLK-070 Surrogate Verifier, BLK-067
Template Composer API) remain in the queue. Complete BLK-169 first as
it's a P0 bug blocking real testing of the P&ID extraction pipeline.
