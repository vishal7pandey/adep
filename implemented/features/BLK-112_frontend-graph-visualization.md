---
id: BLK-112
type: feature
title: "Frontend — graph visualization in Pane 2 + task type selector in wizard"
priority: medium
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:00:00+05:30
estimate: L
depends-on: [BLK-109, BLK-111]
tags: [frontend, graph-visualization, task-types, wizard, pane2]
---

## Description

Update the frontend to support graph extraction task types:

1. **Pane 2** — render graph output (node-link diagram) instead of
   field cards when task_type is "graph_extraction"
2. **Agent Definition Builder** — add task type selection step
3. **Output format selector** — toggle between DEXPI XML, Smart P&ID
   JSON, GraphML views
4. **Topology validation panel** — show rule violations

See vision.md §20.9 for full design.

## Deliverables

### 1. Pane 2 — Graph Visualization

When `task_type === "graph_extraction"`:

- **Node-link diagram** — interactive graph showing equipment
  (rectangles), valves (triangles), instruments (circles), pipes
  (lines). Use a lightweight graph viz library (e.g., react-flow,
  d3-graph, or cytoscape.js).
- **Node detail panel** — click a node → side panel showing:
  - Node type, class, tag
  - Attributes (size, service, etc.)
  - Grounding bbox → click to highlight in Pane 3
  - Confidence badge
- **Edge detail** — click an edge → show connection type, path
  bboxes in Pane 3
- **Output format tabs** — tabs at top:
  - "Graph View" (default) — visual node-link diagram
  - "DEXPI XML" — syntax-highlighted XML
  - "Smart P&ID JSON" — syntax-highlighted JSON
  - "GraphML" — syntax-highlighted XML
- **Topology validation panel** — collapsible panel showing:
  - Green checkmark for each satisfied rule
  - Red warning for each violation with the node/edge involved

### 2. Agent Definition Builder — Task Type Step

Add a new first step to the wizard: **"What do you want to do?"**

- Card 1: **Extract Data** (extraction) — "Extract fields from
  documents like invoices, receipts, and forms"
- Card 2: **Convert Diagram** (graph_extraction) — "Convert
  engineering diagrams like P&IDs to structured formats (DEXPI,
  Smart P&ID, GraphML)"
- Card 3: **Classify Document** (classification) — "Tag documents
  with categories or labels" (disabled — coming soon)
- Card 4: **Transform Document** (transformation) — "Convert
  documents to different representations" (disabled — coming soon)

The selected task type determines:
- Which contracts (templates) are available
- Which tools are shown
- Which skills are compatible

### 3. Template Editor — Graph Contracts

When editing a graph extraction contract:
- Show node type builder (add/remove node types + subtypes)
- Show edge type builder (add/remove edge types + constraints)
- Show topology rule builder (add/remove rules as text or structured)
- Show output format checkboxes

## Acceptance Criteria

- [ ] Pane 2 renders node-link diagram for graph extraction results
- [ ] Clicking a node highlights its bbox in Pane 3
- [ ] Clicking an edge highlights its path in Pane 3
- [ ] Output format tabs switch between graph view and serialized formats
- [ ] Topology validation panel shows rule violations
- [ ] Agent Definition Builder has task type selection as first step
- [ ] Template Editor adapts to task type (field builder vs graph builder)
- [ ] Existing extraction UI works unchanged when task_type = "extraction"

## Notes

- Use react-flow (https://reactflow.dev/) for graph visualization —
  it's React-native, supports custom nodes, and handles pan/zoom
- For syntax highlighting, use react-syntax-highlighter or shiki
- The graph data comes from `GraphExtractionResult.graph` in the
  API response — `{nodes: [], edges: []}`
- Keep the existing field card grid for extraction tasks — don't
  break what works
