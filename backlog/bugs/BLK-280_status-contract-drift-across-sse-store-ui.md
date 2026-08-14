---
id: BLK-280
type: bug
title: "Frontend, SSE, and persisted store each define a different run-status contract"
priority: critical
status: backlog
phase: 1
owner: devin
created: 2026-08-09T11:30:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [status-contract, sse, frontend, backend, analytics, drift]
---

## Description

The project defines multiple status vocabularies for the same lifecycle. The backend uses internal run states, the SSE layer emits semantic completion states, the persisted store stores a separate shape, and the frontend models a reduced state machine. These are not aligned with one another.

This is a classic contract-drift bug: the system says “we have a status model,” but different layers are speaking different languages.

## Problem Statement

Current drift includes:

- backend internal statuses: planning, acting, observing, reflecting, complete, partial, error, paused, cancelled
- persisted store status values: queued, running, paused, completed, failed, cancelled
- SSE completion events: `success`, `failed`, `cancelled`, `max_iterations_reached`, `paused`
- frontend state: `idle`, `running`, `paused`, `completed`, `stopped`

The same run can be reported as `completed`, `success`, `max_iterations_reached`, `partial`, `failed`, or `stopped` depending on which layer is interpreting it. That means the UI, analytics, and exports are not referencing a single truth source.

The root cause is not UI-only; it is a full-stack schema mismatch. This breaks resumption logic, session history, analytics, and user trust because the same run can be classified differently depending on which API is read.

## Acceptance Criteria

- [ ] Define one canonical run-status enum that all layers agree on
- [ ] Persisted store, SSE event payloads, and frontend state map to that canonical enum without lossy translation
- [ ] Terminal states distinguish success, partial, failed, cancelled, paused, and running
- [ ] Frontend and analytics consume the same status contract rather than a separate UI-only taxonomy
- [ ] Tests cover a run crossing backend->store->SSE->frontend without status degradation

## Constraints

- Preserve backward compatibility with existing persisted records and older session history
- Do not collapse distinct states into a generic success/failure bucket in the storage layer
- Treat the canonical enum as the source of truth for all new status traffic

## Dependencies

- `src/api/run_engine.py`
- `src/api/run_executor.py`
- `src/api/sse.py`
- `src/api/routes/runs.py`
- `frontend/context/WorkbenchContext.tsx`
- `frontend/lib/analytics.ts`
- `frontend/components/workbench/Pane1AgentConsole.tsx`
- BLK-187, BLK-188, BLK-192

## Notes

- This is the direct “frontend/backend status contract drift” issue
- It is a systemic integration bug, not just a missing state label

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
