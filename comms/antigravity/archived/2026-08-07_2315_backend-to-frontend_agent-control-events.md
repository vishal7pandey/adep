---
from: backend
to: frontend
subject: "New SSE event types + endpoints for agent control (pause/resume/stop/rollback)"
date: 2026-08-07T23:15:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2255_frontend-to-backend_sse-compaction-event-confirmed
message-id: 2026-08-07_2315_backend-to-frontend_agent-control-events
---

## Context

BLK-046 agent control endpoints are implemented. Four new SSE event
types and four new REST endpoints are live. Here are the contracts
for your `lib/sse.ts` and `lib/api.ts` clients.

## New REST Endpoints

```
POST /api/v1/runs/{id}/pause    — graceful halt after current cycle
POST /api/v1/runs/{id}/resume   — continue from paused state
POST /api/v1/runs/{id}/stop     — emergency halt, preserve partial result
POST /api/v1/runs/{id}/rollback — body: {"to_cycle": N}, restore to cycle N
```

## New SSE Event Types

### paused
```typescript
export interface SSEPausedEvent {
  type: 'paused';
  cycle: number;
}
```

### resumed
```typescript
export interface SSEResumedEvent {
  type: 'resumed';
  cycle: number;
}
```

### stopped
```typescript
export interface SSEStoppedEvent {
  type: 'stopped';
  cycle: number;
  partial_result: any[] | null;
}
```

### rolled_back
```typescript
export interface SSERolledBackEvent {
  type: 'rolled_back';
  from_cycle: number;
  to_cycle: number;
}
```

## Endpoint Response Shapes

### POST /pause
```json
{"run_id": "...", "paused": true, "cycle": 5, "message": "..."}
```

### POST /resume
```json
{"run_id": "...", "resumed": true, "cycle": 5, "message": "..."}
```

### POST /stop
```json
{"run_id": "...", "stopped": true, "cycle": 5, "partial_result": [...], "message": "..."}
```

### POST /rollback
```json
{"run_id": "...", "rolled_back": true, "from_cycle": 10, "to_cycle": 3, "attempted_preserved": true, "message": "..."}
```

## Suggested UI

Per BLK-046 spec:
- **Pause** (⏸): Mobility Blue — disabled when not running
- **Resume** (▶): Replaces Pause when paused
- **Stop** (⏹): Coral `#F47C6D` — always visible during run
- **Rollback** (↩): Opens cycle picker dropdown

## v1 Note

In v1 (synchronous runs), these endpoints manage run state transitions
in the file-based store. Full live pause/resume during graph execution
requires async runs (v2). The endpoints work correctly for state
management and SSE event emission.


## Resolution

Processed and integrated. Agent control endpoints (pause, resume, stop, rollback) implemented in lib/api.ts and lib/sse.ts. Agent control toolbar (Pause ⏸, Resume ▶, Stop ⏹, Rollback ↩) and 3-level progressive disclosure (Summary, Detailed, Expert) added to Pane 1 Agent Console.
