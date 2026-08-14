---
id: BLK-221
type: bug
title: "Status mapping canonicalizes partial and failed outcomes into success-like states"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T11:05:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [status, analytics, frontend, backend, partial, anti-data, trust]
---

## Description

The system collapses multiple real outcomes into a smaller success-like status vocabulary. Internal status values such as `PARTIAL`, `ERROR`, `CANCELLED`, and `PAUSED` are mapped or persisted into success channels, which makes the platform appear healthier and more deterministic than it actually is.

This is a classic anti-data pattern: the model is discarding the information needed to reason reliably.

## Problem Statement

The code does several things that flatten the truth:

- `src/api/run_engine.py` maps `RunStatus.PARTIAL` to `"completed"`
- `frontend/components/workbench/Pane1AgentConsole.tsx` treats `success` and `max_iterations_reached` as the same completed outcome
- UI state models collapse `failed`, `cancelled`, and partial states into generic `stopped` or `completed`
- analytics count every `completed` run as success without distinguishing partial or exhausted runs

This creates false confidence in every downstream place that uses status as an operational truth source: dashboards, leaderboards, filter logic, session history, and worker health.

## Acceptance Criteria

- [ ] Internal run states retain a distinct status for partial, failed, cancelled, paused, and completed
- [ ] Serialization and SSE events preserve the real outcome label until the user explicitly asks for a summarized state
- [ ] Frontend state models distinguish completed-vs-partial-vs-failed in UI and analytics
- [ ] Metrics dashboards expose separate counts for success, partial, failed, paused, cancelled
- [ ] Status compression is only used as a presentation layer and never as the persisted source of truth

## Constraints

- Do not silently coerce partial/exhausted results into success
- Maintain backward compatibility with older persisted run records
- Ensure session history and analytics are truthful even when older data is mixed with new schema fields

## Dependencies

- `src/api/run_engine.py`
- `src/api/run_executor.py`
- `frontend/context/WorkbenchContext.tsx`
- `frontend/components/workbench/Pane1AgentConsole.tsx`
- `frontend/lib/analytics.ts`
- BLK-187, BLK-188

## Notes

- This is an anti-data and anti-logic problem: information about failed or partial runs is being erased before it reaches the UI or analytics
- The project’s quality claims are vulnerable because the “success” metric is no longer grounded in the actual outcome distribution

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
