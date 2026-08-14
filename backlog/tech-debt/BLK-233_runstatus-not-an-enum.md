---
id: BLK-233
type: tech-debt
title: "RunStatus is a plain class with string constants, not an Enum — no type safety, allows arbitrary status strings"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T14:25:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [backend, state, types, type-safety, run-lifecycle]
---

## Description

`src/agent/state.py:338-349` defines `RunStatus` as a plain class:

```python
class RunStatus:
    """Status values for the run lifecycle."""
    PLANNING = "planning"
    ACTING = "acting"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    COMPLETE = "complete"
    PARTIAL = "partial"
    PAUSED = "paused"
    ERROR = "error"
    CANCELLED = "cancelled"
```

This is not a Python `Enum`. There's no type safety — any string can be assigned to a status field, which is exactly how `"rolled_back"` ended up in the codebase (BLK-215) and how the run executor uses a completely different set of string literals (BLK-232).

## Problem Statement

- No type safety: `status: str = "anything_i_want"` compiles and runs without error
- IDE autocomplete doesn't discover the valid values reliably (plain class attributes vs enum members)
- mypy can't catch invalid status assignments because the type is `str`, not `RunStatus`
- The `PageStatus` class in the same file IS a proper `str, Enum` — so the codebase is inconsistent in its own conventions
- The `GapType` in `validator.py` is also a proper `str, Enum` — `RunStatus` is the outlier

## Acceptance Criteria

- [ ] Convert `RunStatus` to `class RunStatus(str, Enum)` with the same values
- [ ] Update `AgentState.status` type annotation from `str` to `RunStatus`
- [ ] Update all code that assigns to `status` to use `RunStatus.PLANNING` etc. instead of string literals
- [ ] Run mypy to catch any type mismatches
- [ ] This is a prerequisite for BLK-232 (status vocabulary unification)

## Constraints

- Converting to Enum may break code that compares `status == "planning"` with string literals — update to `status == RunStatus.PLANNING` or `status.value == "planning"`
- The `str, Enum` pattern ensures `RunStatus.PLANNING == "planning"` still works for backward compatibility

## Dependencies

- `src/agent/state.py`
- All code that reads or writes `AgentState.status`
- Related to BLK-232 (status mismatch) — this is a prerequisite

## Notes

- Found during full-repo audit; `PageStatus` and `GapType` in the same codebase use proper Enums, making `RunStatus` the inconsistent outlier

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
