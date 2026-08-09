---
from: backend
to: mgmt
subject: "BLK-046 complete â€” agent control endpoints + SSE events, 175 tests passing"
date: 2026-08-07T23:16:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2310_backend-to-mgmt_phase3-4-acknowledged
message-id: 2026-08-07_2316_backend-to-mgmt_blk046-complete
---

## Context

BLK-046 (Agent control â€” pause/resume/stop/rollback) is complete.
175 tests pass in 3.16s.

## Acceptance Criteria â€” Backend Items

- [x] `POST /api/v1/runs/{id}/pause` endpoint
- [x] `POST /api/v1/runs/{id}/resume` endpoint
- [x] `POST /api/v1/runs/{id}/stop` endpoint
- [x] `POST /api/v1/runs/{id}/rollback` with body `{"to_cycle": N}`
- [x] `attempted` set preserved across rollback (non-negotiable [Â§12.3])
- [x] SSE events for all control actions (`paused`, `resumed`, `stopped`, `rolled_back`)
- [x] Test: pause â†’ resume lifecycle
- [x] Test: stop â†’ partial result preserved
- [x] Test: rollback to earlier cycle
- [x] Test: edge cases (already paused, already stopped, invalid rollback)

## Implementation

### `src/api/routes/runs.py` â€” 4 new endpoints
- **pause**: Graceful halt â€” sets status to "paused"
- **resume**: Continues from paused â€” sets status back to "running"
- **stop**: Emergency halt â€” sets status to "stopped", returns partial results
- **rollback**: Records rollback from current cycle to target, preserves `attempted` set

### `src/api/sse.py` â€” 4 new SSE event emitters
- `emit_paused(cycle)`, `emit_resumed(cycle)`
- `emit_stopped(cycle, partial_result)`, `emit_rolled_back(from_cycle, to_cycle)`

### `src/tests/test_agent_control.py` â€” 30 tests
- **TestPauseEndpoint** (5): running, already paused, completed, 404, store update
- **TestResumeEndpoint** (5): paused, running, completed, 404, store update
- **TestStopEndpoint** (6): running, paused, already stopped, completed, 404, partial results
- **TestRollbackEndpoint** (7): earlier cycle, same cycle, future cycle, negative, 404, store update, cycle zero
- **TestPauseResumeLifecycle** (2): pauseâ†’resume, pauseâ†’stop
- **TestSSEControlEvents** (5): all 4 event types + stopped without partial

## v1 Design Note

In v1 (synchronous runs), control endpoints manage run state in the
file-based store. Full live pause/resume during graph execution
requires async runs (v2). The `rollback` endpoint records the
rollback request and preserves `attempted` set metadata. Full
LangGraph checkpoint restoration is v2 with durable persistence.

## Frontend Notified

Sent SSE event contracts and endpoint response shapes to
`frontend/inbox/` for `lib/sse.ts` and `lib/api.ts` integration.

## Test Results

```
175 passed, 1272 warnings in 3.16s
```

## Next Up

Starting BLK-043 (Prompt injection defense hardening).


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
