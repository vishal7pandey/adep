---
id: BLK-024
type: feature
title: "run(definition, input) wiring through API"
priority: high
status: backlog
phase: 2
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-016, BLK-017]
tags: [api, run-engine, platform, core]
---

## Description

Wire the run() function through the API layer. The API receives a definition
ID + document, loads the definition from the store, instantiates the run,
and streams progress via WebSocket. This connects the Phase 1 engine to the
Phase 2 platform.

## Acceptance Criteria

- [ ] Run Engine loads AgentDefinition from Definition Store
- [ ] Resolves skill_ref and template_ref to actual objects
- [ ] Builds ToolRegistry from definition's tool_names
- [ ] Invokes run() with resolved objects + document
- [ ] Emits streaming events (thoughts, tool calls, results) for WebSocket
- [ ] Handles run errors gracefully (structured error response)
- [ ] Integration test

## Dependencies

- BLK-016 (AgentDefinition model)
- BLK-017 (Definition Store)
- Phase 1 complete (run, skills, templates, tools)

## Notes

- vision.md §3.5 (Run Instance), §10 Phase 2 step 10
- This is the bridge between engine and platform
