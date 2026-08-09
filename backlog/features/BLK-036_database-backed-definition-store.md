---
id: BLK-036
type: feature
title: "Database-backed Definition Store (v2)"
priority: high
status: backlog
phase: 5
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: L
depends-on: []
tags: [persistence, database, v2, scaling]
---

## Description

Migrate the Definition Store from file-based to database-backed. Needed
when the number of definitions/skills/templates grows or when multi-user
access is required.

## Acceptance Criteria

- [ ] Database schema for definitions, skills, templates
- [ ] Migration script from file-based to database
- [ ] Same CRUD interface (drop-in replacement)
- [ ] Connection pooling
- [ ] Tests

## Constraints

- Database choice requires mgmt approval (architecture decision)

## Dependencies

- Phase 2 complete (file-based store must work first)

## Notes

- vision.md §9 (file-based v1, database v2), §10 Phase 4
