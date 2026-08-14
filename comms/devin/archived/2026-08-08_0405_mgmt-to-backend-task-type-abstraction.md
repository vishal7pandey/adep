---
from: mgmt
to: backend
subject: "Architectural evolution — Task Type Abstraction + P&ID → DEXPI (BLK-109/110/111)"
date: 2026-08-08T04:05:00+05:30
priority: high
status: done
message-id: 2026-08-08_0405_mgmt-to-backend-task-type-abstraction
---

## Context

The user asked: "can we convert a P&ID diagram to Smart P&ID, or
DEXPI format?" and "structured extraction cannot be the only output
format, right?"

They're right. The current architecture is hardcoded to flat field
extraction. I've designed a **Task Type Abstraction** that
generalizes the platform to support graph extraction, classification,
and transformation — all backward compatible with existing code.

Full design: **vision.md §20** (new section, 290 lines).

## What I Did

- Added §20 to vision.md with full architectural design
- Created 3 backlog items: BLK-109, BLK-110, BLK-111

## The Abstraction (BLK-109) — Phase A

**Generalize the output model without breaking anything:**

1. `Template` → `OutputContract` hierarchy
   - `FieldExtractionContract` (current behavior, alias for Template)
   - `GraphExtractionContract` (new — nodes, edges, topology rules)

2. `ExtractedResult` → `RunResult` hierarchy
   - `FieldExtractionResult` (current, alias for ExtractedResult)
   - `GraphExtractionResult` (new — graph + grounding + serialized output)

3. Validator dispatches by `task_type`
   - Extraction: current field-level checks (unchanged)
   - Graph: node coverage, edge connectivity, topology rules, tag format

4. `AgentDefinition` gets `task_type` field (default: "extraction")

**Key constraint: ALL 745 existing tests must pass unchanged.** This
is pure refactoring + new base classes. No existing behavior changes.

## Graph Extraction Tools (BLK-110) — Phase B

8 new tools, all additive (don't touch existing tools):

| Tool | Purpose |
|------|---------|
| `detect_symbols` | Find engineering symbols in a diagram |
| `classify_symbol` | Classify a detected symbol (valve, pump, etc.) |
| `detect_connections` | Find pipe lines connecting symbols |
| `trace_line` | Follow a pipe line through a diagram |
| `read_tag` | Read + parse ISA-5.1 instrument tags |
| `build_graph` | Construct topology graph from symbols + connections |
| `validate_topology` | Check graph against topology rules |
| `serialize_graph` | Convert graph to DEXPI XML / Smart P&ID JSON / GraphML |

File structure: `src/tools/graph/` with submodules for detection,
connection, tag reading, graph building, and serialization.

## P&ID → DEXPI (BLK-111) — Phase C

The first graph extraction use case:

- `PnIDContract` — node types (equipment, valve, instrument, pipe,
  fitting), edge types (connected_to, branches_from, measures,
  controls), topology rules, output formats
- `PnIDSkill` — 7-step probe order (title block → legend → symbols →
  tags → connections → topology → serialize), 4 invariants, failure
  actions for new GapTypes
- `def-pnid-to-dexpi` prebuilt agent definition
- Sample P&ID diagrams in `sample-data/pid/`

## New GapTypes

Add to the validator's `GapType` enum:
- `SYMBOL_UNCLASSIFIED`
- `TAG_UNREADABLE`
- `CONNECTION_AMBIGUOUS`
- `TOPOLOGY_VIOLATION`
- `NODE_MISSING`
- `EDGE_MISSING`
- `ATTRIBUTE_MISSING`
- `SERIALIZATION_FAILED`

## Recommended Execution Order

1. **BLK-109** (abstraction) — refactor first, prove no regressions
2. **BLK-110** (tools) — implement graph extraction tools
3. **BLK-111** (P&ID) — skill + contract + definition + tests

BLK-109 is the foundation. Do not start BLK-110 until BLK-109 is
complete and all existing tests pass.

## Also Still Pending

Don't forget the earlier items:
- **BLK-108** (empty template fields) — fix before e2e tests
- **uv migration** — migrate to pyproject.toml + uv.lock
- **BLK-103** (e2e smoke tests) — prove the app works

Suggested order:
1. uv migration (quick)
2. BLK-108 (empty fields fix)
3. BLK-103 (e2e tests)
4. BLK-109 (task type abstraction)
5. BLK-110 (graph tools)
6. BLK-111 (P&ID skill)

## Resolution

BLK-109 complete. OutputContract + RunResult hierarchies implemented.
TaskValidator dispatches by task_type. AgentDefinition has task_type
field. 8 new GapTypes added. 28 new tests. 782 total tests pass.
Reply sent to mgmt/inbox/.
