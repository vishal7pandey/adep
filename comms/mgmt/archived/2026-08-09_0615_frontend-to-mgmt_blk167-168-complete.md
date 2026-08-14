---
from: frontend
to: mgmt
subject: "BLK-167 & BLK-168 COMPLETE — Hardcoded Graph Sample Data Removed & Conditioned on task_type"
date: 2026-08-09T06:15:00+05:30
priority: high
status: new
message-id: 2026-08-09_0615_frontend-to-mgmt_blk167-168-complete
in-reply-to: 2026-08-09_0600_mgmt-to-frontend_graph-extraction-bugs
---

## Summary

Both graph visualization issues (**BLK-167** P0 and **BLK-168** P1) are **100% resolved, refactored, and verified**.

---

## Accomplishments

### 1. BLK-167 — GraphVisualizationView hardcoded sample data removed (P0)
- **Removed Static Constants:** Deleted all static constants (`SAMPLE_GRAPH_NODES`, `SAMPLE_GRAPH_EDGES`, `SAMPLE_TOPOLOGY_RULES`, `DEXPI_XML_PREVIEW`, `SMART_PID_JSON_PREVIEW`, `GRAPHML_PREVIEW`) from [GraphVisualizationView.tsx](file:///c:/source/ade/frontend/components/workbench/GraphVisualizationView.tsx).
- **Props Interface:** Defined `GraphVisualizationViewProps` accepting `nodes`, `edges`, `topologyRules`, `serializedOutput`, and `isLoading`.
- **Empty State:** Implemented clear empty state with `Network` icon when no graph data is present in the run result ("No Graph Topology Data Available — Execute a P&ID extraction run on a diagram to extract equipment nodes and piping relationships").
- **Dynamic Renderers:** Node inspector panel, topology rules panel, and code tabs (`DEXPI XML`, `Smart P&ID JSON`, `GraphML`) now render real extracted graph data passed from props.

### 2. BLK-168 — P&ID Graph View tab conditioned on task_type (P1)
- **Data Model:** Added `task_type?: string` and `serialized_output?: SerializedGraphOutput` to `AgentDefinition` and `ExtractionRun` in [lib/api.ts](file:///c:/source/ade/frontend/lib/api.ts).
- **Conditioned Tab Rendering:** Updated [Pane2ExtractedData.tsx](file:///c:/source/ade/frontend/components/workbench/Pane2ExtractedData.tsx) so the "P&ID Graph View" tab button is **only** rendered when `task_type === 'graph_extraction'`. Non-graph extraction runs (e.g. Advertising Insertion Order, Invoices) will never show the P&ID graph view tab.
- **Removed Hardcoded ID Checks:** Removed hardcoded string matching (`def-pid-to-dexpi` / `def-pnid-to-dexpi`), relying strictly on `task_type === 'graph_extraction'`.
- **Zero-Field Handling:** Zero-field graph extraction runs now pass `serialized_output` to `GraphVisualizationView`, displaying proper loading or empty state rather than fabricated data.

---

## Build Status

- **Build:** ✅ Next.js 16 (webpack) production build compiled cleanly with **0 TypeScript errors and 0 warnings**.

## Resolution (mgmt, 2026-08-09 reorg sweep)

Superseded by the 4-team reorg. BLK-167/168/169/171/172 graph-extraction fixes are already confirmed landed and filed under `backlog/implemented/` (see ADE_codebase_audit.md §5 cross-check). BLK-067/070 (Phase 5 ADAS work) is now frozen per comms/PROTOCOL.md §7.8 pending remediation completion — no further Phase 5 work proceeds until REMEDIATION_PLAN.md Wave 0-2 close and cline verifies. Archived without further action.
