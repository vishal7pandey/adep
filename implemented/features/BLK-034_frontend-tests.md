---
id: BLK-034
type: feature
title: "Frontend tests — unit + e2e"
priority: medium
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-028, BLK-029, BLK-030, BLK-031]
tags: [frontend, tests, quality]
---

## Description

Unit and end-to-end tests for the frontend. Unit tests for components and
API client; e2e tests for the full user flow (create definition → run →
view result).

## Acceptance Criteria

- [ ] Unit tests for API client (mocked fetch)
- [ ] Unit tests for SSE client (mocked EventSource)
- [ ] Unit tests for key components (Agent Console, Extracted Data, Document Viewer, Skill Editor, Template Editor)
- [ ] Unit tests for ActiveHighlightContext (Pane 2 ↔ Pane 3 linking)
- [ ] E2e test: create skill → create template → create definition → run → view result across 3 panes
- [ ] E2e test: click field in Pane 2 → bbox highlights in Pane 3
- [ ] E2e test: click bbox in Pane 3 → field scrolls into view in Pane 2
- [ ] All tests pass in CI

## Dependencies

- BLK-028 through BLK-031, BLK-033, BLK-038 (all major UI components)

## Notes

- Use Vitest for unit tests, Playwright for e2e
