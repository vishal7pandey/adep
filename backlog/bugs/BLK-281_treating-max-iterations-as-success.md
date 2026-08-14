---
id: BLK-281
type: bug
title: "Max-iterations and exhausted-run states are treated as if the run succeeded"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T11:35:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [max-iterations, partial, frontend, backend, analytics, success-bias]
---

## Description

The system exposes an exhausted-run outcome (`max_iterations_reached`) but the front-end and analytics layers treat it as a success-like completion. This is a real trust problem because the run did not achieve a trustworthy outcome, but it still presents itself as “done.”

## Problem Statement

The runtime may mark a run partial or exhausted when it hits loops, gaps, or cap exhaustion. Yet the SSE event model and UI still map that path to `success` or `completed` in key places.

Examples observed in the code:

- `src/api/run_engine.py` emits `"max_iterations_reached"` on completion events
- `frontend/components/workbench/Pane1AgentConsole.tsx` treats `success` and `max_iterations_reached` as the same final completion path
- `frontend/lib/analytics.ts` counts `run.status === 'completed'` as success without separate logic for exhausted runs
- `src/api/run_engine.py` maps `RunStatus.PARTIAL` to the frontend `completed` status

This results in exhausted runs being counted as victories, which contaminates benchmark claims and the user experience.

## Acceptance Criteria

- [ ] `max_iterations_reached` is retained as a distinct terminal state until intentionally summarized by the UI
- [ ] Exhausted runs are not counted as success in analytics or leaderboards without an explicit labeled override
- [ ] User-visible badges, alerts, and action flows distinguish exhausted runs from fully successful runs
- [ ] Persisted run records retain enough information to distinguish `success`, `partial`, `max_iterations_reached`, and `failed`
- [ ] Test coverage includes an exhausted run and asserts it is not treated as success by default

## Constraints

- Keep legacy runs renderable even if they were persisted under older state names
- Avoid user-visible churn beyond honest state labeling
- Separate true completion from “business still needs review” in reports and UI

## Dependencies

- `src/api/run_engine.py`
- `src/api/sse.py`
- `frontend/components/workbench/Pane1AgentConsole.tsx`
- `frontend/lib/analytics.ts`
- BLK-187, BLK-188, BLK-192, BLK-195

## Notes

- This is another direct instance of status flattening masquerading as progress
- The system is rewarding exhausted runs with success semantics, which is the opposite of trustworthy reporting

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
