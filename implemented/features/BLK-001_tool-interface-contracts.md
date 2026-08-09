---
id: BLK-001
type: feature
title: "Lock tool interface contracts (ToolSpec, Grounding, ToolResult)"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [tools, contracts, foundation]
---

## Description

Define the core type contracts that all tools implement: `ToolSpec` (arg
schemas, return schemas, descriptions), `Grounding` (bbox + provenance),
`ToolResult` (ok/err + data + grounding), and `ToolFunc` protocol. Include
the geometry-tool split (§2.3): auto-estimating `deskew`/`auto_orient` vs
agent-supplied `rotate`.

This is the foundation — every other Phase 1 item depends on these types
being locked.

## Acceptance Criteria

- [ ] `ToolSpec` dataclass with name, description, arg_schema, return_schema
- [ ] `Grounding` type with bbox, page, confidence
- [ ] `ToolResult` with ok, data, grounding, tool, error (structured error, not exception — §2.7)
- [ ] `ToolFunc` Protocol with runtime_checkable
- [ ] `ToolRegistry` class with register, get, call, specs, names
- [ ] Unit tests for registry (register, lookup, invoke, duplicate, unknown)
- [ ] All types have type hints (Python 3.10+ syntax) [TH]

## Constraints

- Must follow vision.md §2.3 (atomic, image-centric tools)
- Must follow vision.md §2.7 (state carries handles, not pixels)
- No external dependencies beyond pydantic

## Dependencies

None. This is the first item.

## Notes

- vision.md §2.3, §10 Phase 1 step 1
- Existing `src/tools/base.py` has a first draft — review and finalize
- Existing tests in `src/tests/test_registry.py` should pass after refinement
