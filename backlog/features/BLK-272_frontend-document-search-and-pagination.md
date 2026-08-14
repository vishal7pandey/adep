---
id: BLK-272
type: feature
title: "Document list and run history need pagination and search"
priority: low
status: backlog
phase: 5
owner: unassigned
created: 2026-08-09T10:45:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [frontend, api, scalability, ux]
---

## Description

`GET /api/v1/documents` and `GET /api/v1/runs` return **all** records unfiltered and unpaginated. Both the backend endpoints and the frontend `fetchRecentRuns(limit)` / documents list have no server-side pagination or search. As the store grows (BLK-124 caching, more runs), this will become a UX and performance problem:

- Large pages (tens of thousands of runs) will be slow to render
- No way to search for a specific document or run
- No way to page through history
- Frontend loads entire dataset into memory

This is a low-priority feature but a real gap for usability as the platform accumulates runs and documents.

## Feature Request

- Backend: add `page`, `page_size`, and `query` params to `GET /api/v1/documents` and `GET /api/v1/runs`
- Backend: return a paginated envelope `{ items, total, page, page_size }`
- Frontend: add pagination controls to run history & document list
- Frontend: add a search box to filter by document filename / definition

## Acceptance Criteria

- [ ] Backend supports pagination on both endpoints
- [ ] Backend supports a simple text query filter (filename / run ID / definition name)
- [ ] Frontend renders page controls and search input
- [ ] Empty states handled cleanly

## Constraints

- Must not break existing callers (CLI, tests, other integrations)
- The paginated envelope shape should match `{items, total, page, page_size}` for consistency

## Dependencies

- None

## Notes

- `fetchRecentRuns` already handles both array and `{items: [...]}` shapes — API addition is compatible
- Related to BLK-118 (batch processing queue) which will increase run volume