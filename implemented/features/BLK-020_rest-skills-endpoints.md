---
id: BLK-020
type: feature
title: "REST: /skills endpoints (CRUD)"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-017, BLK-018]
tags: [api, rest, skills, platform]
---

## Description

REST endpoints for CRUD operations on Skills. Skills are editable through
the frontend Skill Editor.

## Acceptance Criteria

- [ ] GET /skills — list all skills
- [ ] GET /skills/{id} — get one skill
- [ ] POST /skills — create a skill
- [ ] PUT /skills/{id} — update a skill
- [ ] DELETE /skills/{id} — delete a skill
- [ ] Input validation
- [ ] Integration tests

## Dependencies

- BLK-017 (Definition Store)
- BLK-018 (FastAPI scaffold)

## Notes

- Frontend Skill Editor consumes these endpoints
