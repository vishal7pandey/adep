---
id: BLK-022
type: feature
title: "REST: /runs endpoints (start + status + result)"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-018, BLK-024]
tags: [api, rest, runs, platform]
---

## Description

REST endpoints for starting extraction runs and checking their status.

## Acceptance Criteria

- [ ] POST /runs — start a run (definition_id + document upload)
- [ ] GET /runs/{id} — get run status + result
- [ ] GET /runs — list runs (with pagination)
- [ ] File upload handling for documents
- [ ] Returns run ID immediately, status polled or streamed via WebSocket
- [ ] Integration tests

## Dependencies

- BLK-018 (FastAPI scaffold)
- BLK-024 (run engine wiring)

## Notes

- POST /runs starts async; WebSocket (BLK-023) streams progress
