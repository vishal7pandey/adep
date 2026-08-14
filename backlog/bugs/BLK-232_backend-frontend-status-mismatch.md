---
id: BLK-232
type: bug
title: "Backend RunStatus and frontend ExtractionRun status are completely mismatched — 9 backend values vs 6 frontend values with zero overlap"
priority: high
status: backlog
phase: 2
owner: devin
created: 2026-08-09T14:20:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [api, frontend, status, bug, mismatch, run-lifecycle]
---

## Description

The backend `RunStatus` class (`src/agent/state.py:338-349`) defines these status values:
- `PLANNING = "planning"`
- `ACTING = "acting"`
- `OBSERVING = "observing"`
- `REFLECTING = "reflecting"`
- `COMPLETE = "complete"`
- `PARTIAL = "partial"`
- `PAUSED = "paused"`
- `ERROR = "error"`
- `CANCELLED = "cancelled"`

The frontend `ExtractionRun` interface (`frontend/lib/api.ts:128`) defines:
```typescript
status: 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'stopped';
```

**Zero overlap except `paused`.** The backend says `"complete"`, the frontend expects `"completed"`. The backend says `"error"`, the frontend expects `"failed"`. The backend says `"cancelled"`, the frontend expects `"stopped"`. The backend has `"planning"`, `"acting"`, `"observing"`, `"reflecting"`, `"partial"` — none of which exist in the frontend type. The frontend has `"idle"` and `"running"` — neither of which exist in `RunStatus`.

Additionally, the `RunExecutor` (`src/api/run_executor.py:90`) uses string literals `"queued"`, `"running"`, `"paused"`, `"completed"`, `"failed"`, `"cancelled"` — a third set of status values that partially matches the frontend but doesn't match `RunStatus`.

And the rollback endpoint (`src/api/routes/runs.py:688`) sets `status = "rolled_back"` — a value that exists in **none** of these three sets.

## Problem Statement

- The backend agent state, the API run executor, and the frontend all use different status vocabularies — there is no single source of truth
- The SSE replay code in `runs.py:479-487` maps `completed` → `success`, `cancelled` → `cancelled`, `failed` → `failed`, else → `max_iterations_reached` — a fourth mapping layer
- The frontend can never correctly display the agent's current phase (planning, acting, observing, reflecting) because those values don't exist in the TypeScript type
- The `RunStatus` class is not an `Enum` — it's a plain class with string constants, so there's no type safety preventing arbitrary status strings like `"rolled_back"`
- The store (`definitions/store.py`) persists whatever status string is written, meaning the database can contain any of these values with no validation

## Acceptance Criteria

- [ ] Define a single `RunStatus` enum (or string literal union) used by all three layers: agent state, run executor, and frontend
- [ ] The status vocabulary should include: `queued`, `running`, `paused`, `completed`, `partial`, `failed`, `cancelled` at minimum
- [ ] Optionally expose the agent's current phase (planning/acting/observing/reflecting) as a separate `agent_phase` field, not as the run status
- [ ] Update `RunStatus` in `src/agent/state.py` to be a proper `str, Enum` with the agreed values
- [ ] Update `RunExecutor` to use `RunStatus` enum values instead of string literals
- [ ] Update `frontend/lib/api.ts` `ExtractionRun.status` to match the backend enum
- [ ] Add a migration or validation step for existing stored runs with old status values
- [ ] Remove `"rolled_back"` from the rollback endpoint (BLK-215) — use `paused` or `cancelled` instead

## Constraints

- Don't break existing API consumers — the SSE complete event mapping may need to stay
- The frontend needs to handle all status values gracefully (loading indicators, error states, etc.)

## Dependencies

- `src/agent/state.py` (`RunStatus`)
- `src/api/run_executor.py` (`RunContext.status`)
- `src/api/routes/runs.py` (status mapping in SSE replay, rollback endpoint)
- `frontend/lib/api.ts` (`ExtractionRun.status`)
- `frontend/lib/sse.ts` (`SSECompleteEvent.status`)
- Related to BLK-215 (rollback sets invalid status)

## Notes

- Found during full-repo audit; this is a fundamental contract mismatch between the backend and frontend that likely causes silent UI bugs where the frontend can't match the status string and falls through to default rendering

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
