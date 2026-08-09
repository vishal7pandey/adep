---
id: BLK-017
type: feature
title: "Definition Store — file-based CRUD for definitions, skills, templates"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-016]
tags: [definitions, store, persistence, platform]
---

## Description

Implement a file-based Definition Store that provides CRUD operations for
agent definitions, skills, and templates. v1 uses a local `.adep/` folder
on disk with JSON files. Simple, inspectable, version-controllable,
sufficient for single-user v1 [SF].

The `.adep/` folder structure:
```
.adep/
  definitions/     # Agent definition JSON files
  skills/          # Skill JSON files
  templates/       # Template JSON files
  runs/            # Run traces and results (JSON)
```

## Acceptance Criteria

- [ ] `src/definitions/store.py` with DefinitionStore class
- [ ] CRUD: create, read, update, delete for definitions, skills, templates
- [ ] List all definitions/skills/templates
- [ ] File-based: JSON in `.adep/` folder on disk
- [ ] `.adep/` folder created on first run if it doesn't exist
- [ ] Run traces and results also persisted to `.adep/runs/`
- [ ] Validation on create/update (schema integrity)
- [ ] Unit tests

## Constraints

- File-based v1 — no database, no Redis, no cloud storage [SF]
- `.adep/` folder is the single persistence location
- Database migration deferred to v2

## Dependencies

- BLK-016 (AgentDefinition model)

## Notes

- vision.md §9 (Local persistence: .adep/ folder), §10 Phase 2 step 8+11
