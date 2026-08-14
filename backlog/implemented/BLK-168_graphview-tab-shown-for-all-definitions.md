# BLK-168: P&ID Graph View tab shown unconditionally for all definition types

- **Priority:** P1 — High
- **Status:** implemented
- **Owner:** unassigned
- **Phase:** 5
- **Type:** bug
- **Reported:** 2026-08-08
- **Resolved:** 2026-08-09

## Resolution

Verified against current code (2026-08-09): `Pane2ExtractedData.tsx` computes `isGraphTask = runMeta?.taskType === 'graph_extraction'` from the fetched run's real `task_type` and gates both the tab and the zero-field fallback on it. Moved from `backlog/bugs/` to `backlog/implemented/`; see BLK-192 for the process gap that let this sit unmoved.

## Problem

`Pane2ExtractedData.tsx` shows the "P&ID Graph View" tab button unconditionally for all runs, regardless of the definition's `task_type`. A user running an "Advertising Insertion Order" extraction sees a P&ID graph tab, clicks it, and sees fabricated graph data (BLK-167).

Additionally, when `fields.length === 0` and the definition ID matches `def-pid-to-dexpi` or `def-pnid-to-dexpi`, the component falls back to rendering `GraphVisualizationView` unconditionally — even if the run failed or produced no graph data.

## Root Cause

The view mode tabs are hardcoded with no task_type awareness. The fallback condition checks definition ID strings instead of the definition's `task_type` field.

## Files Affected

- `frontend/components/workbench/Pane2ExtractedData.tsx` — lines 243-268 (tab buttons), lines 364-373 (zero-field fallback)

## Fix

1. Fetch the definition's `task_type` from the run metadata (run result should include `task_type` — requires BLK-169)
2. Only show "P&ID Graph View" tab when `task_type === "graph_extraction"`
3. For zero-field runs with graph_extraction definitions, show an appropriate empty/loading state instead of fabricated graph data
4. For non-graph-extraction definitions, never show graph view

## Acceptance Criteria

- [ ] "P&ID Graph View" tab only visible when definition task_type is `graph_extraction`
- [ ] Non-graph-extraction runs never show graph view
- [ ] Zero-field graph extraction runs show empty state, not fabricated data
- [ ] Definition task_type is sourced from run metadata, not hardcoded ID matching
