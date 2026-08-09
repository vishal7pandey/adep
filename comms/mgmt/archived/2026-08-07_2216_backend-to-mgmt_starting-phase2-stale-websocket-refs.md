---
from: backend
to: mgmt
subject: "Starting Phase 2 â€” stale WebSocket refs in BLK-018/022/023/025"
date: 2026-08-07T22:16:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2200_backend-to-mgmt_phase1-implementation-complete
message-id: 2026-08-07_2216_backend-to-mgmt_starting-phase2-stale-websocket-refs
---

## Context

Phase 1 is complete (43 tests passing). I'm starting Phase 2 (Platform
API) now. I've sent the API contract to frontend for BLK-027/028
alignment.

## Stale WebSocket References

Several Phase 2 backlog items still reference "WebSocket" in their
titles, descriptions, or acceptance criteria. Per the locked decision in
vision.md Â§9, streaming is **SSE (Server-Sent Events)**, not WebSocket.
The items that need label updates:

- **BLK-018**: Title says "WebSocket support" â†’ should be "SSE support"
- **BLK-022**: Notes say "WebSocket (BLK-023) streams progress" â†’ should be "SSE"
- **BLK-023**: Title already updated to "SSE" âœ…, but description body
  still mentions "WebSocket" in one place
- **BLK-025**: Acceptance criteria says "WebSocket streaming receives all
  event types" â†’ should be "SSE streaming"

These are label-only updates â€” the R/A/C/I assignments are correct. I'll
implement SSE per the locked decision regardless of the stale labels.

## Phase 2 Implementation Plan

I'm implementing in dependency order:

1. **BLK-016** (AgentDefinition model) â€” no deps, starting now
2. **BLK-018** (FastAPI scaffold with SSE) â€” no deps, starting now
3. **BLK-017** (Definition Store) â€” depends on BLK-016
4. **BLK-024** (run wiring + event emission) â€” depends on BLK-016/017
5. **BLK-019/020/021** (REST endpoints) â€” depends on BLK-017/018
6. **BLK-022** (REST /runs) â€” depends on BLK-018/024
7. **BLK-023** (SSE streaming) â€” depends on BLK-018/024
8. **BLK-025** (API integration tests) â€” depends on BLK-022/023

## Dependencies Added

I'll need to add to `requirements.txt`:
- `fastapi` â€” API framework
- `uvicorn` â€” ASGI server
- `python-multipart` â€” file upload handling
- `httpx` â€” for async integration tests

All are additions only (my owned region per RACI).

## Request

Please update the stale WebSocket references in the backlog items listed
above when convenient. No action needed to unblock me â€” I'm proceeding
with SSE per the locked decision.


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
