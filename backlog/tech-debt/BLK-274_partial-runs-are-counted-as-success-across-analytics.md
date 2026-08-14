---
id: BLK-274
type: tech-debt
title: "Stop counting partial and exhausted runs as full success across analytics"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T10:30:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [analytics, metrics, status, reporting, frontend, backend]
---

## Description

The current reporting model overstates success by flattening partial outcomes into `completed` and then treating every `completed` run as a success in analytics. This is not a cosmetic issue; it affects benchmark interpretation, leaderboards, trend charts, and operational trust in the platform’s metrics.

## Problem Statement

Today:

- `src/api/run_engine.py` maps `RunStatus.PARTIAL` to `"completed"`
- the frontend receives `max_iterations_reached` over SSE but persists the run as `completed`
- `frontend/lib/analytics.ts` counts every `run.status === 'completed'` as success

That means:

- exhausted runs with unresolved gaps inflate success rate
- definition leaderboards over-credit incomplete extractions
- time-series charts cannot separate perfect completion from partial salvage
- analytics cannot answer basic questions like “how often do we finish cleanly vs. with gaps?”

## Acceptance Criteria

- [ ] Persist enough status detail to distinguish full completion from partial/exhausted completion
- [ ] Analytics KPIs expose separate counts for success, partial, failed, and cancelled runs
- [ ] Existing success-rate charts use a clearly defined numerator that excludes incomplete outcomes unless explicitly configured otherwise
- [ ] Leaderboards and summaries surface partial-rate alongside success-rate where relevant
- [ ] Historical mixed-status data has a documented normalization strategy

## Constraints

- Avoid breaking current run list views while introducing richer outcome categories
- Preserve backward compatibility for historical records that only store `completed`
- Coordinate with UI badge/state updates so metrics and visuals stay aligned

## Dependencies

- Depends conceptually on `BLK-181`
- Likely touches `src/api/run_engine.py`, persisted run schema, and `frontend/lib/analytics.ts`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
