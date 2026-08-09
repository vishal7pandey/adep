---
id: BLK-138
type: bug
title: "Remove stub mode from ReAct plan node — silently no-ops in production"
priority: high
status: done
started: 2026-08-08T14:20:00+05:30
completed: 2026-08-08T14:30:00+05:30
phase: 4
owner: backend
created: 2026-08-08T14:10:00+05:30
estimate: S
depends-on: []
tags: [backend, bug, stub-mode, production-readiness, critical]
---

## Problem

`src/agent/graph.py` lines 108-114 contain a "stub mode" that
silently no-ops when `llm_client`, `skill`, or `registry` is `None`:

```python
if llm_client is None or skill is None or registry is None:
    # Stub mode: no LLM, no action — used during scaffolding
    return {
        "step": step,
        "status": RunStatus.PLANNING,
        "_planned_action": None,
    }
```

This was added during initial scaffolding. It is still in production
code. If any of these three dependencies is `None` at runtime, the
agent enters an infinite loop of no-op planning steps that never
extracts anything, never errors, and never terminates — until the
recursion limit hits and the run returns an empty result with no
explanation.

### Why This Is Dangerous

1. **Silent failure**: The run appears to execute (status is
   `PLANNING`, not `FAILED`) but produces nothing. No error, no
   exception, no log entry explaining why.
2. **Infinite loop**: Each no-op increments `step` but never changes
   state, so the graph keeps calling the plan node until
   `recursion_limit` is hit.
3. **Wasted budget**: The run consumes a slot in the executor and
   runs to the recursion limit doing nothing.
4. **Misleading trace**: The trace shows planning steps with no
   action, giving no indication that a dependency was missing.

### When Could This Happen in Production?

- A provider import fails silently (e.g., `paddleocr` not installed,
  `openai` package missing) and the registry is built with zero tools
- A skill lookup fails and returns `None`
- A configuration error leaves the LLM client uninitialized
- Any future code path that passes `None` by mistake

All of these should be **loud failures**, not silent no-ops.

## Fix

### Option A: Raise immediately (recommended)

Replace the stub mode with a clear error:

```python
if llm_client is None:
    raise RuntimeError(
        "Cannot plan: LLM client is None. Check Azure API key "
        "and endpoint configuration."
    )
if skill is None:
    raise RuntimeError(
        f"Cannot plan: skill is None. Check skill lookup for "
        f"'{state.get('skill_name', 'unknown')}'."
    )
if registry is None:
    raise RuntimeError(
        "Cannot plan: tool registry is None. Check provider "
        "configuration and imports."
    )
```

### Option B: Fail at graph construction

Move the check to `build_react_graph()` so the failure happens before
the run starts, not mid-loop. This is cleaner but requires verifying
that `build_react_graph` has access to all three dependencies at
construction time (it does — they're passed as arguments).

### Either way: remove the stub mode entirely

The `# Stub mode` comment and the no-op return must be deleted. No
production code path should silently continue with missing
dependencies.

### Additional: validate registry is non-empty

In `build_tool_registry()` (`src/run.py`), after building the
registry, check that it has at least one tool. If the provider import
failed silently and no tools were registered, raise:

```python
if len(registry.names()) == 0:
    raise RuntimeError(
        f"Tool registry is empty. Check provider configuration: "
        f"ocr_provider={settings.ocr_provider}, "
        f"vlm_provider={settings.vlm_provider}. "
        f"Ensure required packages are installed."
    )
```

## Acceptance Criteria

- [x] Stub mode removed from `plan_node` in `src/agent/graph.py`
- [x] Missing `llm_client`, `skill`, or `registry` raises
      `RuntimeError` with a descriptive message
- [x] `build_tool_registry()` raises if zero tools registered
- [x] No "stub mode" or "scaffolding" comments remain in production code
- [x] Tests: missing LLM client raises, missing skill raises, missing
      registry raises, empty registry raises
- [x] Tests: existing tests that pass `None` for these dependencies
      are updated to expect `RuntimeError` instead of no-op
- [x] No regression in existing 782 tests (785 total with 3 new)

## Notes

This is a small fix with high impact. The stub mode was a scaffolding
shortcut that should have been removed before the first production
release. It is a silent-failure antipattern that violates the
platform's own design principle of loud, auditable failures.
