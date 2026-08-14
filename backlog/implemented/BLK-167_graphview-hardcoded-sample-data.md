# BLK-167: GraphVisualizationView renders hardcoded sample data instead of real run output

- **Priority:** P0 — Critical
- **Status:** implemented
- **Owner:** unassigned
- **Phase:** 5
- **Type:** bug
- **Reported:** 2026-08-08
- **Resolved:** 2026-08-09

## Resolution

Verified against current code (2026-08-09): `GraphVisualizationView.tsx` now declares a real `GraphVisualizationViewProps` interface and takes `nodes`, `edges`, `topologyRules`, `serializedOutput` as props; no `SAMPLE_*` constants remain in the file. Moved from `backlog/bugs/` to `backlog/implemented/` — this file was left in `backlog/bugs/` with `Status: backlog` after the fix landed, which is itself a process gap tracked in BLK-192.

## Problem

`GraphVisualizationView.tsx` renders 100% hardcoded sample data — `SAMPLE_GRAPH_NODES`, `SAMPLE_GRAPH_EDGES`, `SAMPLE_TOPOLOGY_RULES`, `DEXPI_XML_PREVIEW`, `SMART_PID_JSON_PREVIEW`, `GRAPHML_PREVIEW` are static constants baked into the component. The component accepts no props, fetches no API data, and completely ignores the actual run result.

When a user runs a P&ID extraction and views the "P&ID Graph View" tab, they see fabricated equipment tags (P-101A, V-204, PIT-301, T-102), fake line numbers, and fake DEXPI/GraphML output that has no relationship to the actual document. This is misleading and constitutes a data integrity issue.

## Root Cause

The component was built as a UI prototype/mockup and was never wired to real data. It is the same class of bug as BLK-166 (mock data in analytics dashboard).

## Files Affected

- `frontend/components/workbench/GraphVisualizationView.tsx` — all sample constants (lines 35-120) and the component body (lines 122-290) that references them

## Fix

1. Remove all `SAMPLE_*` and `*_PREVIEW` constants
2. Accept run data as props (graph nodes, edges, topology rules, serialized outputs) from the parent `Pane2ExtractedData`
3. The parent should pass graph data from the run result's `serialized_output` field (requires BLK-169 backend support)
4. Show empty state when no graph data is available
5. Never display fabricated data under any circumstances

## Acceptance Criteria

- [ ] No hardcoded graph data constants exist in the component
- [ ] Component receives graph data via props from parent
- [ ] Empty state shown when run has no graph output
- [ ] DEXPI XML, Smart P&ID JSON, and GraphML tabs render from actual `serialized_output` in run result
- [ ] Node inspector panel shows real attributes from extracted graph
- [ ] Topology rules panel shows real validation results from `validate_topology` tool
