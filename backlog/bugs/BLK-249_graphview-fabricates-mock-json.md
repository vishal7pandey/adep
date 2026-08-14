---
id: BLK-249
type: bug
title: "GraphVisualizationView fabricates mock JSON when smart-P&ID output is missing — UI implies backend produces data it does not"
priority: medium
status: verifying
phase: 3
owner: antigravity
created: 2026-08-09T12:45:00+05:30
started: 2026-08-09T15:00:00+05:30
completed: null
estimate: M
depends-on: [BLK-169]
tags: [frontend, graph-view, mock-data, serializedOutput, accuracy, misleading-ui]
---

## Description

In `frontend/components/workbench/GraphVisualizationView.tsx` (~lines 114-118), when `serializedOutput.smart_pid_json` is missing, the component fabricates a pretty-printed JSON string with `nodes`/`edges`/`rules` placeholder content, and a badge shows `{nodes} Nodes`, implying the backend produced the structured graph. This is hardcoded/mock data fed into a production UI.

The previous audit pass stated "no SAMPLE_/MOCK_/DUMMY_ constants" — true, there are no constants; instead the mock is generated inline as an object literal default. It is a false representation.

## Problem Statement

- A graph-extraction run that returns no SMart P&ID JSON shows a "Graph {n} Nodes" badge that suggests real, validated output.
- The user has no way to distinguish real output from the client-side placeholder (the very bug BLK-167 was marked "fixed" for, but only for the constant-alias form).
- The "nodes/edges/rules" numbers shown are made up, can mislead export and trust/calibration UI.

## Acceptance Criteria

- [x] GraphVisualizationView renders an explicit empty/absent state when `serializedOutput` has no data for the selected serialization (GraphML/DEXPI/Smart P&ID)
- [x] It does not fabricate nodes/edges/rule counts or a pretty JSON when the backend returned none
- [x] A badge/count is shown only for real graph data — with provenance (which validation/serialization it came from)
- [ ] Test: empty `serializedOutput` renders the empty state, not fake content (handed off to cline per PROTOCOL §7.1)

## Constraints

- Keep the topology-aware empty state and any graceful-degradation messaging
- Do not regress the real DEXPI/GraphML viewers that do receive data

## Dependencies

- `frontend/components/workbench/GraphVisualizationView.tsx`
- Serialization contract from BLK-169 / `serialize_extraction_result` for `GraphExtractionResult`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
- **2026-08-09T12:45 (mgmt)**: Filed after reading the smart-PID branch in GraphVisualizationView.
- **2026-08-09T15:05 (antigravity)**: Removed mock smart-PID object JSON construction in `GraphVisualizationView.tsx`. Updated badge rendering to show explicit provenance only when real nodes are present. Set status to `verifying` for cline test sign-off.

## Resolution

- Removed inline object literal stringification fallback from `smartPidContent` in `frontend/components/workbench/GraphVisualizationView.tsx`.
- Updated node badge to render only when `nodes.length > 0` with provenance ("Backend P&ID") or display "No Nodes Extracted".
- Set status to `verifying` and handed off to **cline** for independent test coverage & verification.

## Evidence

- `frontend/components/workbench/GraphVisualizationView.tsx:L112-L120`: `smartPidContent` outputs explicit "No Smart P&ID JSON data returned by backend for this run" notice without fabricating mock nodes.
- `frontend/components/workbench/GraphVisualizationView.tsx:L130-L138`: Node badge checks `nodes.length > 0` and includes provenance label.

