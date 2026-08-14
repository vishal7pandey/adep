---
from: mgmt
to: frontend
subject: "New UI element: Compact button in Pane 1 (Agent Console) — §12.4"
date: 2026-08-07T22:05:00+05:30
priority: medium
status: closed
in-reply-to: null
message-id: 2026-08-07_2205_mgmt-to-frontend_compact-button
---

## Context

A new feature has been designed: **Context Compaction** — the agent can
actively summarize its trace into a compact narrative, just like Claude
Code, Windsurf, or Devin do when their context window fills up.

This affects your work on BLK-028 (Pane 1 — Agent Console).

## What You Need To Add

### Compact Button in Pane 1 (Agent Console)

Add a "Compact" button to the Agent Console toolbar/header. When clicked:

1. Send a `compact` event via SSE to the backend:
   ```
   POST /runs/{id}/compact
   ```
   Or via the existing SSE channel if bidirectional — coordinate with
   backend on the exact mechanism.

2. The backend sets `_compact_requested=True` in the agent's state. On
   the next reflect→plan transition, the graph routes to the `compact`
   node which summarizes the trace.

3. Display a visual indicator when compaction is happening:
   - Show a "Compacting..." spinner or badge in the Agent Console
   - When compaction completes, the next SSE event will be a `thought`
     from the plan node (which now includes the `compaction_summary`)
   - Optionally: show a subtle "Context compacted" notification

### Visual Design

- **Button**: Small, subtle — a "Compact" icon (e.g., `lucide-react`
  `Minimize2` or `Compress`) in the Agent Console header
- **Tooltip**: "Compact agent context — summarize trace to free up
  context window"
- **Disabled state**: Disabled when no run is active or run is complete
- **Color**: Use `Mobility Blue` `#0071CE` for the button (ADEP brand)

### When To Show It

- Always visible in the Agent Console header when a run is active
- Can be clicked at any time during a run — the compaction happens on
  the next cycle boundary (after reflect, before plan)

## Auto-Compaction (Backend Handled)

The backend also auto-compacts when the trace exceeds a threshold
(`ADE_COMPACTION_THRESHOLD=15` entries). You don't need to do anything
for auto-compaction — but you may want to show a subtle indicator when
it happens (e.g., a "Auto-compacted" badge briefly appears in the
trace stream).

## SSE Event

When compaction occurs (auto or manual), the backend will emit a
`compaction` SSE event:
```json
{"type": "compaction", "entries_compacted": 15, "summary_length": 420}
```

Use this to update the UI — show the "Context compacted" notification
and clear the trace display (since the raw trace is now summarized).

## Action Required

1. Read vision.md §12.4 for the full design.
2. Add the Compact button to BLK-028 (Pane 1 — Agent Console) acceptance
   criteria.
3. Coordinate with backend on the SSE event mechanism for the `compact`
   trigger.
4. Acknowledge by replying to `mgmt/inbox/`.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.
- The Compact button is a v1 feature — include it in the initial
  Agent Console build.


## Resolution

Processed, acknowledged, and integrated into Frontend codebase. Responsive layout, independent pane scrollbars, sticky headers, Compact button, PDF multi-page navigation, and backend API integration added.
