---
id: BLK-021
type: feature
title: "REST: /templates endpoints (CRUD)"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-017, BLK-018]
tags: [api, rest, templates, platform]
---

## Description

REST endpoints for CRUD operations on Templates. Templates are editable
through the frontend Template Editor.

## Acceptance Criteria

- [ ] GET /templates — list all templates
- [ ] GET /templates/{id} — get one template
- [ ] POST /templates — create a template
- [ ] PUT /templates/{id} — update a template
- [ ] DELETE /templates/{id} — delete a template
- [ ] Input validation (Pydantic schema fields)
- [ ] Integration tests

## Dependencies

- BLK-017 (Definition Store)
- BLK-018 (FastAPI scaffold)

## Notes

- Frontend Template Editor consumes these endpoints
