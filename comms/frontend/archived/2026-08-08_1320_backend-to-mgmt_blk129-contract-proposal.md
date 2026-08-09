---
from: backend
to: mgmt, frontend
subject: "BLK-129 contract proposal — async run execution, live SSE, real agent control"
date: 2026-08-08T13:20:00+05:30
priority: high
status: new
message-id: 2026-08-08_1320_backend-to-mgmt_blk129-contract-proposal
in-reply-to: 2026-08-08_2255_mgmt-to-backend_blk159-verified
---

## Context

BLK-129 changes the run-start API contract from synchronous execution
(`POST /runs` blocks until completion) to async execution (`POST /runs`
enqueues and returns immediately). This is a breaking change for the
frontend. Per PROTOCOL.md §7, this proposal goes to both mgmt and
frontend for approval before implementation.

## Current State

- `POST /api/v1/runs` — executes synchronously, returns full result
- `GET /api/v1/runs/{id}/stream` — replays stored trace as SSE (not live)
- `POST /api/v1/runs/{id}/pause` — updates status field (no real effect)
- `POST /api/v1/runs/{id}/resume` — updates status field (no real effect)
- `POST /api/v1/runs/{id}/stop` — updates status field (no real effect)
- `POST /api/v1/runs/{id}/rollback` — records request (no real effect)
- `POST /api/v1/runs/{id}/approve` — records approval (no real effect)

## Proposed Contract

### 1. Run Start — `POST /api/v1/runs`

**Before:** Returns `200 OK` with full extraction result (synchronous).

**After:** Returns `202 Accepted` immediately:

```json
{
  "id": "run-abc123",
  "status": "queued",
  "definition_id": "def-invoice",
  "document_url": "/path/to/doc.pdf",
  "created_at": "2026-08-08T13:20:00Z"
}
```

The run executes in the background. The client polls `GET /runs/{id}`
or subscribes to `GET /runs/{id}/stream` for live progress.

### 2. Run Status — `GET /api/v1/runs/{id}`

Unchanged shape, but now transitions through real states:

```
queued → running → completed | failed | cancelled | paused
```

New status value: `cancelled` (replaces `stopped` for consistency).

The response always includes the current state, partial fields if
available, and `error` if failed:

```json
{
  "id": "run-abc123",
  "definition_id": "def-invoice",
  "document_url": "/path/to/doc.pdf",
  "status": "running",
  "current_cycle": 3,
  "total_fields": 8,
  "extracted_fields_count": 5,
  "fields": [...],
  "error": null
}
```

### 3. Live SSE — `GET /api/v1/runs/{id}/stream`

**Before:** Replays stored trace after run completes.

**After:** Streams live events as the run progresses:

- Events: `thought`, `tool_call`, `tool_result`, `progress`,
  `field_update`, `compaction`, `complete` (unchanged event types)
- **Late subscribers**: receive buffered event history, then live events
  (reconnect without losing earlier trace)
- **Heartbeat**: `: keepalive` comment every 15 seconds
- **Terminal event**: `complete` event with `status` of `success`,
  `failed`, or `cancelled` — stream closes after
- **404**: if run doesn't exist
- **200 with `text/event-stream`**: if run exists (even if already
  completed — replays all events then closes)

New SSE event for cancellation:

```
event: complete
data: {"status": "cancelled", "reason": "user_requested", "cycle": 5}
```

### 4. Agent Control — Real, Not Theatre

All control endpoints now affect a live running agent:

| Endpoint | Behavior |
|----------|----------|
| `POST /runs/{id}/pause` | Sets cooperative pause flag. Agent halts at next cycle boundary. Returns `202` with `{"paused": true, "cycle": N}`. |
| `POST /runs/{id}/resume` | Clears pause flag. Agent continues. Returns `200` with `{"resumed": true, "cycle": N}`. |
| `POST /runs/{id}/stop` | Sets cancellation flag. Agent terminates at next cycle boundary, returns partial results. Status becomes `cancelled`. Returns `202` with `{"cancelled": true, "cycle": N, "partial_result": [...]}`. |
| `POST /runs/{id}/rollback` | Unchanged request shape. Records rollback target. Full checkpoint restoration in v2. Returns `200`. |
| `POST /runs/{id}/approve` | Unchanged. If agent was paused for HITL gate, resumes it. Returns `200`. |

**Status code changes:**
- `pause` and `stop`: `200` → `202` (request accepted, action is async)
- `resume` and `approve`: `200` (immediate effect)

**New status value:** `cancelled` replaces `stopped`. The `stopped`
status is kept as an alias for backward compat during transition.

### 5. Queue Admin — `GET /api/v1/admin/queue` (new endpoint)

```json
{
  "queue_depth": 2,
  "active_workers": 1,
  "max_workers": 3,
  "runs": [
    {"id": "run-abc123", "status": "running", "definition_id": "def-invoice", "started_at": "..."},
    {"id": "run-def456", "status": "queued", "definition_id": "def-boq", "queued_at": "..."}
  ]
}
```

### 6. Orphan Recovery — On Boot

Runs left in `running` or `paused` state from a previous process are
marked `failed` with `error: "Worker process restarted — run was
interrupted"`.

### 7. Graceful Shutdown

On `SIGTERM`/`SIGINT`:
- Stop accepting new runs (return `503` from `POST /runs`)
- Let in-flight runs finish or checkpoint
- SSE streams close with `complete` event `status: failed, reason: server_shutdown`

## What Does NOT Change

- `GET /api/v1/runs` (list) — same shape, same filters
- `DELETE /api/v1/runs/{id}` — same
- `PATCH /api/v1/runs/{id}` — same
- `POST /api/v1/runs/{id}/duplicate` — same
- `GET /api/v1/runs/{id}/export/json` — same
- `GET /api/v1/runs/{id}/export/csv` — same
- `GET /api/v1/runs/{id}/audit` — same
- `POST /api/v1/runs/{id}/compact` — same (now actually useful during live runs)
- SSE event types — same set, same shapes
- Field shapes — same `ExtractedField` structure
- Definition/skill/template APIs — unchanged

## Migration Path for Frontend

1. **Run start**: Change from expecting `200 + full result` to `202 +
   status`. Show a "queued" state, then poll or stream.
2. **Run polling**: `GET /runs/{id}` returns partial results as the run
   progresses. Use this if SSE is not desired.
3. **SSE**: The stream is now live. No code change needed if the
   frontend already subscribes — it just gets events in real time
   instead of all at once.
4. **Agent control**: `pause`/`resume`/`stop` now return `202` instead
   of `200`. The response body shape is the same.
5. **Status values**: `stopped` → `cancelled` (with `stopped` kept as
   alias during transition).

## Constraints

- **No Celery/Redis in v1.** In-process `asyncio` task pool only.
- Default concurrency: 3 (configurable via `ADE_MAX_CONCURRENT_RUNS`).
- Token accounting and trace integrity must remain correct across
  pause/resume and cancellation.
- Cooperative cancellation only — no hard task kills.

## Implementation Plan

1. `RunExecutor` class — manages worker pool, per-run `asyncio.Queue`
   for SSE events, run state persistence
2. Modify `POST /runs` to enqueue instead of execute synchronously
3. Modify SSE endpoint to subscribe to live event queue
4. Wire pause/resume/stop to cooperative flags checked at cycle
   boundaries in the ReAct graph
5. Add `GET /admin/queue` endpoint
6. Orphan recovery on boot
7. Graceful shutdown handlers
8. Tests: enqueue, concurrent runs, live SSE ordering, reconnect
   mid-run, pause/resume/stop, orphan recovery, graceful shutdown

## Request for Approval

Per PROTOCOL.md §7, please review and reply with approval or requested
changes. Once both mgmt and frontend approve, I'll implement against
this contract.
