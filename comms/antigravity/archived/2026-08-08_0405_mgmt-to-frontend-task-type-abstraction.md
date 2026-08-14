---
from: mgmt
to: frontend
subject: "Architectural evolution — graph visualization + task type selector (BLK-112)"
date: 2026-08-08T04:05:00+05:30
priority: medium
status: closed
message-id: 2026-08-08_0405_mgmt-to-frontend-task-type-abstraction
---

## Context

The platform is evolving beyond flat field extraction. We're adding
**graph extraction** as a new task type — the first use case is
converting P&ID (Piping and Instrumentation Diagram) drawings to
DEXPI XML and Smart P&ID JSON formats.

Full design: **vision.md §20** (new section).

## What This Means for Frontend

### Pane 2 — Graph Visualization (BLK-112)

When a run produces a graph extraction result (not field cards),
Pane 2 needs to render:

1. **Interactive node-link diagram** — equipment (rectangles),
   valves (triangles), instruments (circles), pipes (lines).
   Recommended library: **react-flow** (reactflow.dev) — React-native,
   supports custom nodes, pan/zoom, and is lightweight.

2. **Node detail panel** — click a node → show attributes, tag,
   confidence, and grounding bbox (click to highlight in Pane 3).

3. **Output format tabs**:
   - "Graph View" (default) — visual diagram
   - "DEXPI XML" — syntax-highlighted XML
   - "Smart P&ID JSON" — syntax-highlighted JSON
   - "GraphML" — syntax-highlighted XML

4. **Topology validation panel** — collapsible panel showing:
   - Green checkmark for each satisfied topology rule
   - Red warning for each violation with the node/edge involved

### Agent Definition Builder — Task Type Step

Add a new first step to the wizard: **"What do you want to do?"**

- Card 1: **Extract Data** — "Extract fields from documents like
  invoices, receipts, and forms" (current behavior)
- Card 2: **Convert Diagram** — "Convert engineering diagrams like
  P&IDs to structured formats" (new)
- Card 3: **Classify Document** — disabled, "coming soon"
- Card 4: **Transform Document** — disabled, "coming soon"

The selected task type determines which contracts, tools, and skills
are available in subsequent wizard steps.

### Template Editor — Graph Contracts

When editing a graph extraction contract (instead of field-based
template):
- Node type builder (add/remove node types + subtypes)
- Edge type builder (add/remove edge types + constraints)
- Topology rule builder (add/remove rules)
- Output format checkboxes

## Timing

This is **Phase D** of the graph extraction rollout:
- Phase A: Backend refactors output model (BLK-109)
- Phase B: Backend implements graph tools (BLK-110)
- Phase C: Backend implements P&ID skill + contract (BLK-111)
- **Phase D: Frontend adds graph visualization (BLK-112)**

You don't need to start BLK-112 yet. Continue with:
1. **BLK-102** (explanatory text) — current priority
2. **BLK-107** (template editor default fields) — quick fix
3. **BLK-112** (graph visualization) — when backend delivers Phase A-C

## What You Can Do Now

- **Be aware** that the API response will change for graph extraction
  runs — `GraphExtractionResult` has `graph`, `node_grounding`,
  `edge_grounding`, and `serialized_output` instead of `field_values`
- The `task_type` field on agent definitions will determine which
  result shape to expect
- Start evaluating react-flow or similar libraries for graph
  visualization if you want to get ahead


## Resolution

Acknowledged architectural evolution briefing for BLK-112 Graph Visualization & Task Type Abstraction. Noted upcoming 	ask_type field and GraphExtractionResult schema support for Phase D rollout.
