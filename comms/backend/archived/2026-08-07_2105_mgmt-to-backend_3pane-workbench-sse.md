---
from: mgmt
to: backend
subject: "Vision major update — 3-pane workbench, SSE, .adep/ local persistence"
date: 2026-08-07T21:05:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-07_2105_mgmt-to-backend_3pane-workbench-sse
---

## Context

The vision has been significantly updated. The platform is now defined as
a **local-first workbench** running on a laptop — not a cloud SaaS. This
simplifies the stack dramatically. Three key changes affect your work:

1. **WebSocket → SSE** for streaming
2. **`.adep/` folder** for local persistence (no database, no Redis)
3. **3-pane workbench UI** (frontend change, but affects your SSE event schema)

## What Changed

### 1. SSE replaces WebSocket (BLK-023)

The streaming endpoint is now SSE (Server-Sent Events), not WebSocket.
Rationale: SSE is simpler for unidirectional server→client streaming,
no connection management complexity. Frontend uses `EventSource` API.

**BLK-023 updated:**
- Endpoint: `GET /runs/{id}/stream` (text/event-stream)
- Event format: `data: {"type": "thought", "content": "..."}\n\n`
- Event types: `thought`, `tool_call` (with thumbnail data for crop results),
  `tool_result`, `gap_report`, `progress`, `complete`
- SSE auto-reconnect handles disconnects

**Your action:** When implementing BLK-023, use FastAPI's
`StreamingResponse` with `media_type="text/event-stream"`. The event
schema must include thumbnail data (base64 or URL) for `crop` tool calls
so the frontend can render inline previews in the Agent Console.

### 2. `.adep/` folder for local persistence (BLK-017)

All persistence goes to a local `.adep/` folder on disk:
```
.adep/
  definitions/     # Agent definition JSON files
  skills/          # Skill JSON files
  templates/       # Template JSON files
  runs/            # Run traces and results (JSON)
```

**BLK-017 updated:**
- `.adep/` folder created on first run if it doesn't exist
- Run traces and results also persisted to `.adep/runs/`
- No database, no Redis, no cloud storage [SF]

### 3. SSE Event Schema (coordinate with frontend)

The frontend Agent Console (Pane 1) needs structured events to render
collapsible cards. The event schema you define in BLK-023 directly
drives the frontend. Frontend is Consulted on this schema (RACI §3).

**Proposed event types:**
```typescript
type SSEEvent =
  | { type: "thought", content: string }
  | { type: "tool_call", tool: string, args: Record<string, any>, thumbnail?: string }
  | { type: "tool_result", tool: string, ok: boolean, data: any, grounding?: { bbox: number[], page: number } }
  | { type: "gap_report", gaps: GapReport }
  | { type: "progress", completed: number, total: number, failing: number }
  | { type: "complete", result: ExtractedResult }
```

Send your proposed schema to `mgmt/inbox/` for review before implementing.
Frontend will review via comms as well.

## Updated Backlog Items

- **BLK-017** — `.adep/` folder structure, run persistence
- **BLK-023** — SSE endpoint (was WebSocket)
- **BLK-024** — run(definition, input) wiring (now streams via SSE)

## Action Required

1. Read updated §0.2, §9, §10, §11 in `vision.md`.
2. Review BLK-017 and BLK-023 acceptance criteria changes.
3. **Propose your SSE event schema** to `mgmt/inbox/` before implementing
   BLK-023. Frontend will also provide input.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.
- SSE, not WebSocket — this is a locked decision (§9).
- `.adep/` folder, not database — this is a locked decision (§9).


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
