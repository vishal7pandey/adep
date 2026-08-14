---
id: BLK-182
type: bug
title: "Graph Visualization tab shown for all run types even when no graph data exists"
priority: medium
status: backlog
phase: 5
owner: antigravity
created: 2026-08-09T10:25:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-167, BLK-169]
tags: [frontend, workbench, placeholder, data-integrity]
---

## Description

`Pane2ExtractedData` always renders a "P&ID Graph" / graph visualization tab for every run in the workbench, regardless of the run's definition type. When the user runs a non-P&ID extraction (e.g. an invoice or W-2), the graph tab shows the GraphVisualizationView component that, in its empty state, displays "No Graph Topology Data Available" as filler content.

This is confusing to users: an invoice run should not show a P&ID graph tab at all. The tab should be conditionally rendered only for P&ID runs (or when `serialized_output` graph data is present).

## Acceptance Criteria

- [ ] Graph tab appears only when the run's `task_type` indicates a P&ID-type run or when graph node/edge data is present in `serialized_output`
- [ ] Non-graph runs show no graph tab (clean tab set)
- [ ] Empty state never shown for non-graph runs
- [ ] Tests updated to cover conditional tab visibility

## Constraints

- Do not break existing P&ID graph view (BLK-112)
- Must not rely on hardcoded sample data (BLK-167)

## Dependencies

- BLK-167 (remove hardcoded sample graph data)
- BLK-169 (backend graph extraction support in run engine)

## Notes

- Related to BLK-168 (graphview tab shown for all definitions)
- Found during frontend workbench audit

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
