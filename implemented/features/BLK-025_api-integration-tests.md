---
id: BLK-025
type: feature
title: "API integration tests — full platform flow"
priority: medium
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-022, BLK-023]
tags: [tests, api, integration, platform]
---

## Description

Integration tests covering the full platform flow: create definition →
start run → stream progress → get result. Uses FastAPI TestClient with
mocked LLM and providers.

## Acceptance Criteria

- [ ] Test: create skill → create template → create definition → start run
- [ ] Test: WebSocket streaming receives all event types
- [ ] Test: run completes with correct ExtractedResult
- [ ] Test: error handling (invalid definition, missing document)
- [ ] All tests pass in CI

## Dependencies

- BLK-022 (REST /runs)
- BLK-023 (WebSocket streaming)

## Notes

- Mocked providers only [TS]
