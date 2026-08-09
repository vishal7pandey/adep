---
id: BLK-090
type: bug
title: "Backend: SSE stream replays from stored run, not live — pause/resume/stop are no-ops during execution"
priority: high
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: M
depends-on: []
tags: [backend, bug, sse, run-control, stabilization]
---

## Bug

`src/api/routes/runs.py` lines 83-86 — `start_run` calls
`execute_run` **synchronously** and returns the completed result.
The SSE stream endpoint (`GET /runs/{id}/stream`) then replays
stored trace events.

This means:

1. **`POST /runs` blocks until the entire run completes** — the
   frontend gets the final result, not a run ID to stream from.
2. **Pause/resume/stop endpoints are no-ops** — by the time the
   frontend calls `POST /runs/{id}/pause`, the run is already done.
3. **SSE stream is a replay, not live** — the frontend sees all
   events at once after completion, not real-time progress.
4. **Rollback is a metadata-only stub** — records the request but
   doesn't actually restore state.

## Impact

- The frontend Agent Console can't show real-time progress
- Pause/resume/stop/rollback buttons in Pane1AgentConsole don't work
- The `emitter` passed to `execute_run` is `None` in the `POST /runs`
  path (line 86), so no SSE events are emitted during execution

## Fix

This is a known v1 limitation (noted in comments), but it blocks the
frontend UX. Two options:

### Option A: Background task + emitter (recommended for v1.1)

```python
@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_run(req: StartRunRequest) -> dict[str, Any]:
    # ... validation ...
    run_id = f"run-{uuid.uuid4().hex[:8]}"

    # Create emitter and store it for the SSE endpoint
    emitter = SSEEventEmitter()
    _RUN_EMITTERS[run_id] = emitter

    # Launch in background
    asyncio.create_task(
        execute_run(req.definition_id, req.document_path, emitter=emitter)
    )

    return {
        "id": run_id,
        "definition_id": req.definition_id,
        "document_url": req.document_path,
        "status": "running",
        "current_cycle": 0,
        "total_fields": 0,
        "extracted_fields_count": 0,
        "fields": [],
    }
```

The SSE endpoint then consumes from the live emitter:
```python
@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    emitter = _RUN_EMITTERS.get(run_id)
    if emitter:
        # Live stream
        async def event_stream():
            async for event in emitter.async_iter():
                yield event
        return StreamingResponse(event_stream(), ...)
    else:
        # Fallback: replay stored run (existing behavior)
        ...
```

### Option B: Document the limitation clearly

If async runs are too complex for v1, at minimum:
- Return 200 with the completed result (not 202)
- Remove "stream progress via GET /runs/{id}/stream" from the docstring
- Have pause/resume/stop return 409 Conflict with "Run already completed"
- Update frontend to not show real-time controls during v1

## Acceptance Criteria

- [ ] `POST /runs` returns immediately with a run ID (if Option A)
- [ ] SSE stream shows events in real-time during execution
- [ ] Pause/resume/stop work during live execution
- [ ] OR: v1 limitations clearly documented and frontend adapts
