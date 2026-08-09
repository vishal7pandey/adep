---
id: BLK-003
type: feature
title: "Implement Tool Registry with provider dispatch"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-001]
tags: [tools, registry, foundation]
---

## Description

Implement the ToolRegistry that tools register into with explicit schemas.
The agent sees only tool names + arg schemas + descriptions. Provider
selection is config-driven: `if config.ocr_provider == "paddle": from
providers.ocr_paddle import ocr as _ocr`. One-line swap with zero plugin
infrastructure.

## Acceptance Criteria

- [ ] ToolRegistry.register(spec, func) adds a tool
- [ ] ToolRegistry.get(name) returns the tool function
- [ ] ToolRegistry.call(name, **kwargs) invokes and returns ToolResult
- [ ] ToolRegistry.specs() returns all ToolSpec objects
- [ ] ToolRegistry.names() returns all registered tool names
- [ ] Duplicate registration raises ValueError
- [ ] Unknown tool lookup raises KeyError
- [ ] Config-driven provider dispatch in build_tool_registry()

## Constraints

- No plugin loader — hardcoded if/elif dispatch is fine for v1 [SF]
- Don't build a plugin loader before you have a second plugin [SF]

## Dependencies

- BLK-001 (ToolSpec, ToolResult, ToolRegistry types)

## Notes

- vision.md §9 (ToolRegistry loading decision), §10 Phase 1 step 3
- Existing `src/tools/base.py` and `src/tests/test_registry.py` — refine
