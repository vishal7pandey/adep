---
id: BLK-291
type: tech-debt
title: "run.py docstring says 'to be implemented next' — stale comment from initial scaffolding"
priority: low
status: backlog
phase: 2
owner: devin
created: 2026-08-09T13:35:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [stale, docs, run, agent, scaffolding]
---

## Description

`src/run.py` line 11-12 contains a stale docstring:

```python
"""Run entry point: compose Template + Skill + Document into an extraction run [§3.3].

    ...

This module wires the pieces together. The actual LangGraph graph nodes are
in agent/graph.py (to be implemented next). For now, this provides the
public API and the initial State construction.
"""
```

The LangGraph graph nodes in `agent/graph.py` have been fully implemented (866 lines, with plan/act/observe/reflect/compact/terminate nodes). The "to be implemented next" and "For now" comments are stale from the initial scaffolding phase.

## Problem Statement

- A new developer reading `run.py` would think the agent graph is not yet implemented, when it's been complete for months
- Stale scaffolding comments erode trust in all code comments — if this one is wrong, which others might be?
- The comment contradicts the actual state of the codebase

## Acceptance Criteria

- [ ] Update the docstring to reflect that `agent/graph.py` is fully implemented
- [ ] Remove "to be implemented next" and "For now" language
- [ ] Audit other module docstrings for similar stale scaffolding language

## Constraints

- None — comment-only fix

## Dependencies

- `src/run.py:11-12`

## Notes

- Found during full-repo audit; a minor issue but symptomatic of a codebase that was scaffolded quickly and never cleaned up

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
