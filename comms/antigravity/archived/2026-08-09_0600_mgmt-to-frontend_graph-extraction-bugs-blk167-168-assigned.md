---
from: mgmt
to: frontend
subject: "URGENT: Graph view fabricated data — BLK-167, BLK-168 assigned"
date: 2026-08-09T06:00:00+05:30
priority: high
status: new
message-id: 2026-08-09_0600_mgmt-to-frontend_graph-extraction-bugs
---

## Context: Fabricated P&ID Extraction Output

During testing of `sample-pid-01.jpg`, a user ran the "Advertising
Insertion Order" definition on a P&ID diagram. The run produced
**0 tokens, $0.0000, 0/6 fields grounded** — yet the "P&ID Graph View"
tab in Pane 2 displayed fabricated DEXPI XML, Smart P&ID JSON, and
GraphML output with fake equipment tags (P-101A, V-204, PIT-301,
T-102) that don't exist anywhere in the drawing.

The fabricated data is hardcoded directly in the component source code.

---

## BLK-167 — GraphVisualizationView renders hardcoded sample data (P0)

**This is your top priority.**

`GraphVisualizationView.tsx` contains static constants that are
rendered unconditionally:

- `SAMPLE_GRAPH_NODES` (4 fake nodes: P-101A, V-204, PIT-301, T-102)
- `SAMPLE_GRAPH_EDGES` (3 fake edges with fake line numbers)
- `SAMPLE_TOPOLOGY_RULES` (3 fake validation rules)
- `DEXPI_XML_PREVIEW` (fake DEXPI XML string)
- `SMART_PID_JSON_PREVIEW` (fake Smart P&ID JSON string)
- `GRAPHML_PREVIEW` (fake GraphML string)

The component accepts no props, fetches no API data, and ignores the
actual run result entirely. This is the same class of bug as BLK-166
(mock data in analytics dashboard).

### What needs to happen:

1. Remove all `SAMPLE_*` and `*_PREVIEW` constants
2. Accept run data as props from parent `Pane2ExtractedData`:
   - `nodes: GraphNode[]`
   - `edges: GraphEdge[]`
   - `topologyRules: TopologyRule[]`
   - `serializedOutput: { dexpi_xml: string, smart_pid_json: string, graphml: string }`
3. The parent (`Pane2ExtractedData`) should pass graph data from the
   run result's `serialized_output` field
   (**Note:** This requires backend BLK-169 to populate
   `serialized_output` in run results. Until BLK-169 is complete,
   wire the component to accept props and show an empty state when
   no data is provided.)
4. Show empty state when no graph data is available — never display
   fabricated data under any circumstances
5. Node inspector panel shows real attributes from extracted graph
6. Topology rules panel shows real validation results

### Key files:
- `frontend/components/workbench/GraphVisualizationView.tsx` — all
  sample constants (lines 35-120) and component body (lines 122-290)
- `frontend/components/workbench/Pane2ExtractedData.tsx` — parent
  that renders GraphVisualizationView

### Acceptance criteria:
- [ ] No hardcoded graph data constants exist in the component
- [ ] Component receives graph data via props from parent
- [ ] Empty state shown when run has no graph output
- [ ] DEXPI XML, Smart P&ID JSON, GraphML tabs render from actual
     `serialized_output` in run result
- [ ] Node inspector shows real attributes
- [ ] Topology rules panel shows real validation results

Spec: `backlog/bugs/BLK-167_graphview-hardcoded-sample-data.md`

---

## BLK-168 — P&ID Graph View tab shown for all definitions (P1)

The "P&ID Graph View" tab button is always visible in
`Pane2ExtractedData.tsx` regardless of the definition's `task_type`.
A user running an "Advertising Insertion Order" extraction sees a
P&ID graph tab, clicks it, and sees fabricated data (BLK-167).

Additionally, when `fields.length === 0` and the definition ID
matches `def-pid-to-dexpi` or `def-pnid-to-dexpi`, the component
falls back to rendering `GraphVisualizationView` unconditionally —
even if the run failed or produced no graph data.

### What needs to happen:

1. Check the run result's `task_type` field (requires backend BLK-169
   to include `task_type` in serialized run results)
2. Only show "P&ID Graph View" tab when `task_type === "graph_extraction"`
3. For zero-field graph_extraction runs, show an appropriate
   empty/loading state instead of fabricated graph data
4. For non-graph-extraction definitions, never show graph view
5. Remove the hardcoded definition ID string matching
   (`def-pid-to-dexpi` / `def-pnid-to-dexpi`) — use `task_type` instead

### Key files:
- `frontend/components/workbench/Pane2ExtractedData.tsx` —
  lines 243-268 (tab buttons), lines 364-373 (zero-field fallback)

### Acceptance criteria:
- [ ] "P&ID Graph View" tab only visible when task_type is graph_extraction
- [ ] Non-graph-extraction runs never show graph view
- [ ] Zero-field graph extraction runs show empty state, not fake data
- [ ] task_type sourced from run metadata, not hardcoded ID matching

Spec: `backlog/bugs/BLK-168_graphview-tab-shown-for-all-definitions.md`

---

## Dependency Note

Both BLK-167 and BLK-168 have a dependency on **backend BLK-169**
(run engine graph extraction support) to provide real graph data in
run results. The backend team has been assigned BLK-169 as their
P0 priority.

**You can start immediately on the structural work:**
- Remove hardcoded constants from `GraphVisualizationView.tsx`
- Add props interface and wire parent to pass data
- Add task_type conditional logic for tab visibility
- Add empty states

Until BLK-169 delivers real graph data, the component will show empty
states. Once BLK-169 is complete, the props will flow through
automatically.

---

## Priority Order

1. **BLK-167** (P0) — remove hardcoded data, wire to props
2. **BLK-168** (P1) — conditional tab visibility by task_type

Your existing Phase 5 assignment (BLK-067 UI — Template Composer modal)
remains in the queue. Complete BLK-167 first as it's a P0 data
integrity issue.
