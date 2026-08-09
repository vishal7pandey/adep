---
id: BLK-019
type: feature
title: "REST: /definitions endpoints (CRUD)"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-017, BLK-018]
tags: [api, rest, definitions, platform]
---

## Description

REST endpoints for CRUD operations on Agent Definitions.

## Acceptance Criteria

- [ ] GET /definitions — list all definitions
- [ ] GET /definitions/{id} — get one definition
- [ ] POST /definitions — create a definition
- [ ] PUT /definitions/{id} — update a definition
- [ ] DELETE /definitions/{id} — delete a definition
- [ ] Input validation via Pydantic
- [ ] Error responses with appropriate HTTP codes
- [ ] Integration tests

## Dependencies

- BLK-017 (Definition Store)
- BLK-018 (FastAPI scaffold)

## Notes

- Frontend is Consulted on response shape (RACI §3)
