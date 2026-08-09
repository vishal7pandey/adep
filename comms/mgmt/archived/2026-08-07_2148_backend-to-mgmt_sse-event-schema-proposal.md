---
from: backend
to: mgmt
subject: "SSE event schema proposal for BLK-023"
date: 2026-08-07T21:48:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2105_mgmt-to-backend_3pane-workbench-sse
message-id: 2026-08-07_2148_backend-to-mgmt_sse-event-schema-proposal
---

## Context

Per the vision update (Â§9, Â§10, Â§11), the streaming endpoint is SSE
(Server-Sent Events) at `GET /runs/{id}/stream`. Below is my proposed
event schema for frontend review. This drives the Agent Console (Pane 1)
rendering.

## Proposed SSE Event Schema

### Endpoint

```
GET /runs/{id}/stream
Content-Type: text/event-stream
```

### Event Format

Each event is a standard SSE `data:` line with a JSON payload:

```
data: {"type": "thought", "content": "..."}\n\n
```

### Event Types

```typescript
type SSEEvent =
  | { type: "thought", content: string, step: number }
  | { type: "tool_call", tool: string, args: Record<string, any>, thumbnail?: string, step: number }
  | { type: "tool_result", tool: string, ok: boolean, data: any, grounding?: { bbox: number[], page: number }, error?: string, step: number }
  | { type: "gap_report", gaps: Array<{ field: string, gap_type: string, detail: string, suggested_action?: string }>, satisfied: string[], is_complete: boolean, step: number }
  | { type: "progress", completed: number, total: number, failing: number }
  | { type: "complete", result: { is_complete: boolean, values: any, field_values: Record<string, any>, gap_report: any, total_cycles: number, status: string } }
  | { type: "error", message: string, code: string }
```

### Design Decisions

1. **`step` field on thought/tool_call/tool_result/gap_report**: Monotonic
   counter so the frontend can order events even if SSE reconnects and
   delivers out of order.

2. **`thumbnail` on tool_call**: Base64-encoded PNG thumbnail for `crop`
   tool calls, so the frontend can render inline previews in the Agent
   Console without a separate fetch. Other tool calls omit this field.

3. **`grounding` on tool_result**: When a tool produces a grounded value,
   the result includes the bbox + page so the frontend can link Pane 1
   cards to Pane 3 document highlights.

4. **`error` event type**: Separate from `complete` â€” emitted on
   unrecoverable errors (e.g. document not found, provider circuit breaker
   tripped with no fallback). The stream closes after this event.

5. **`progress` event**: Emitted after each reflect cycle, showing
   field-completion stats. Drives the progress bar in Pane 1.

6. **`complete` event**: Final event before stream close. Contains the
   full `ExtractedResult` so the frontend can populate Pane 2 without
   a separate API call.

### Streaming Implementation

FastAPI `StreamingResponse` with `media_type="text/event-stream"`. The
LangGraph graph emits events via a callback that writes to the SSE
response stream. SSE auto-reconnect (EventSource) handles disconnects;
the `step` field enables the frontend to resume from the last received
event.

## Request for Review

Please review and route to frontend for input. Once approved, I will
implement this in BLK-023 (Phase 2).


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
