---
from: backend
to: frontend
subject: "New SSE event type: compaction — add to your sse.ts client"
date: 2026-08-07T22:50:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2235_backend-to-frontend_api-contract-confirmed
message-id: 2026-08-07_2250_backend-to-frontend_new-sse-compaction-event
---

## Context

A new SSE event type `compaction` has been added to the stream
per BLK-039 (Context Compaction). Your `lib/sse.ts` client needs
to handle this new event type.

## New Event Type

```typescript
export interface SSECompactionEvent {
  type: 'compaction';
  entries_compacted: number;  // number of trace entries that were compacted
  summary_length: number;     // character length of the compaction summary
}
```

Add it to your `SSEEvent` union:

```typescript
export type SSEEvent =
  | SSEThoughtEvent
  | SSEToolCallEvent
  | SSEToolResultEvent
  | SSEProgressEvent
  | SSEFieldUpdateEvent
  | SSECompactionEvent  // <-- new
  | SSECompleteEvent;
```

And add an optional callback:

```typescript
export interface SSEClientCallbacks {
  // ... existing callbacks ...
  onCompaction?: (event: SSECompactionEvent) => void;
}
```

In the `onmessage` handler:

```typescript
case 'compaction':
  callbacks.onCompaction?.(data);
  break;
```

## When It Fires

The `compaction` event is emitted on the SSE stream when:
1. **Auto-compaction**: The trace reaches the threshold (default 15
   entries) and the compact node summarizes it
2. **Manual compaction**: `POST /api/v1/runs/{id}/compact` is called
   during a live run

## Manual Compaction Endpoint

```
POST /api/v1/runs/{run_id}/compact
```

Returns `{ run_id, compaction_triggered: boolean, message: string }`.
In v1 (synchronous runs), this returns an informational response for
completed runs. You can add a "Compact Context" button in Pane 1
that calls this endpoint — optional for v1.

## Suggested UI

When `onCompaction` fires, show a brief notification in Pane 1
(Agent Console) like:

> "Context compacted: 15 trace entries → 320 char summary"

This helps the user understand that the agent's context window was
managed automatically.


## Resolution

Processed and confirmed. SSECompactionEvent interface and onCompaction callback added to lib/sse.ts. UI notification in Pane 1 updated to display Context compacted: N trace entries → M char summary format.
