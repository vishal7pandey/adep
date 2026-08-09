---
id: BLK-018
type: feature
title: "FastAPI app scaffold with CORS and WebSocket support"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [api, fastapi, scaffold, platform]
---

## Description

Scaffold the FastAPI application with CORS middleware, WebSocket support,
health check endpoint, and OpenAPI documentation. This is the foundation
for all Phase 2 REST + WebSocket endpoints.

## Acceptance Criteria

- [ ] `src/api/main.py` with FastAPI app
- [ ] CORS middleware configured for frontend dev server
- [ ] WebSocket endpoint base setup
- [ ] Health check: GET /health
- [ ] OpenAPI docs at /docs
- [ ] App starts with `uvicorn src.api.main:app`

## Dependencies

None (can start in parallel with BLK-016/017)

## Notes

- vision.md §9 (Backend API: FastAPI), §10 Phase 2 step 9
