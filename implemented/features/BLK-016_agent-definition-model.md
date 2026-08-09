---
id: BLK-016
type: feature
title: "AgentDefinition model — serializable composition of bricks"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [definitions, platform, api]
---

## Description

Implement the AgentDefinition model — a serializable composition of skill +
template + tool set + agent config. This is the "blueprint" that users
compose through the UI and that the Run Engine instantiates.

## Acceptance Criteria

- [ ] `src/definitions/base.py` with AgentDefinition Pydantic model
- [ ] Fields: name, version, agent_config, tool_names, skill_ref, template_ref
- [ ] Serializable to/from JSON
- [ ] Validation: skill and template must exist, tool_names must be registered
- [ ] Unit tests

## Dependencies

- Phase 1 complete (skills, templates, tools must exist)

## Notes

- vision.md §0.1 (Agent Definition), §3.4, §10 Phase 2 step 7
- Frontend is Consulted on the data model shape (RACI §1)
