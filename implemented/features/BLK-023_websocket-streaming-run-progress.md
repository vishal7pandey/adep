---
id: BLK-023
type: feature
title: "SSE: streaming run progress to Agent Console"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-018, BLK-024]
tags: [api, sse, streaming, agent-console, platform]
---

## Description

SSE (Server-Sent Events) endpoint that streams real-time run progress to
the frontend Agent Console (Pane 1). Streams: agent thoughts, tool calls
(with inline thumbnail data for crop results), tool results, gap reports,
field-completion progress, and final result. This is what makes the Agent
Console feel "live" — the Devin/Windsurf-style reasoning trace.

SSE over WebSocket: simpler for unidirectional server→client streaming,
no connection management complexity. Frontend uses `EventSource` API.

## Acceptance Criteria

- [ ] SSE endpoint: GET /runs/{id}/stream (text/event-stream)
- [ ] Streams JSON events: thought, tool_call (with thumbnail data), tool_result, gap_report, progress, compaction, complete
- [ ] Event format: `data: {"type": "thought", "content": "..."}\n\n`
- [ ] Compaction event: `{"type": "compaction", "entries_compacted": N, "summary_length": N}`
- [ ] POST /runs/{id}/compact endpoint: triggers manual /compaction [§12.4]
- [ ] Handles client disconnect gracefully (SSE auto-reconnect)
- [ ] Integration test with SSE client (httpx AsyncClient)

## Dependencies

- BLK-018 (FastAPI scaffold)
- BLK-024 (run engine — needs to emit events)

## Notes

- vision.md §0.2 (Pane 1 — Agent Console), §9 (Streaming: SSE)
- Frontend is Consulted on event schema (RACI §3)
