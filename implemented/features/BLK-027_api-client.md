---
id: BLK-027
type: feature
title: "API client — REST + SSE for backend communication"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-026]
tags: [frontend, api-client, rest, sse]
---

## Description

Implement the typed API client that the frontend uses to communicate with
the FastAPI backend. Covers all REST endpoints and SSE streaming for the
Agent Console.

## Acceptance Criteria

- [ ] `frontend/lib/api.ts` with typed REST client
- [ ] Methods: listDefinitions, getDefinition, createDefinition, etc.
- [ ] Methods: listSkills, getSkill, createSkill, etc.
- [ ] Methods: listTemplates, getTemplate, createTemplate, etc.
- [ ] Methods: startRun, getRun, listRuns
- [ ] `frontend/lib/sse.ts` with SSE client: `connectToRun(id, onEvent)` using EventSource
- [ ] SSE event types: thought, tool_call, tool_result, gap_report, progress, complete
- [ ] `frontend/lib/types.ts` with TypeScript types matching backend Pydantic models
- [ ] Error handling with typed error responses

## Dependencies

- BLK-026 (frontend scaffold)
- Phase 2 API contracts agreed (RACI §5)

## Notes

- backend is Consulted on API response shapes
