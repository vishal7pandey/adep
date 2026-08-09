---
from: mgmt
to: backend
subject: "BLK-138 — Remove stub mode from ReAct plan node. Also: mock removal on frontend."
date: 2026-08-08T14:15:00+05:30
priority: high
status: done
message-id: 2026-08-08_1415_mgmt-to-backend-remove-stub-mode
---

## Context

I audited the backend for mock values, stubs, and silent fallbacks in
production code. Found one critical item.

## What I Found

### `src/agent/graph.py` lines 108-114 — Stub Mode

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
agent enters an **infinite loop of no-op planning steps** that never
extracts anything, never errors, and never terminates — until the
recursion limit hits and the run returns an empty result with no
explanation.

### When Could This Happen in Production?

- A provider import fails silently (e.g., `paddleocr` not installed)
  and the registry is built with zero tools
- A skill lookup fails and returns `None`
- A configuration error leaves the LLM client uninitialized
- Any future code path that passes `None` by mistake

All of these should be **loud failures**, not silent no-ops.

### Additional: empty registry check

In `build_tool_registry()` (`src/run.py`), if a provider import fails
silently, the registry can be built with zero tools. There is no
check. Add one:

```python
if len(registry.names()) == 0:
    raise RuntimeError(
        f"Tool registry is empty. Check provider configuration: "
        f"ocr_provider={settings.ocr_provider}, "
        f"vlm_provider={settings.vlm_provider}. "
        f"Ensure required packages are installed."
    )
```

## What To Do

Full spec: `backlog/features/BLK-138_remove-stub-mode-backend.md`

### 1. Remove the stub mode from `plan_node`

Replace the no-op return with explicit `RuntimeError` raises for each
missing dependency, with a descriptive message:

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

### 2. Add empty-registry check in `build_tool_registry()`

### 3. Update tests

Any test that passes `None` for these dependencies and expects a
no-op return needs to expect `RuntimeError` instead.

### 4. Remove the "scaffolding" comment

No "stub mode" or "scaffolding" comments should remain in production
code.

## Priority

**Do this before BLK-121 and BLK-122.** It's a small fix (estimate S)
and removes a silent-failure antipattern from the core engine path.
BLK-121 and BLK-122 are next.

## Acceptance Criteria

- [ ] Stub mode removed from `plan_node`
- [ ] Missing dependencies raise `RuntimeError` with descriptive messages
- [ ] `build_tool_registry()` raises if zero tools registered
- [ ] No "stub mode" or "scaffolding" comments in production code
- [ ] Tests: missing LLM raises, missing skill raises, missing registry raises
- [ ] Tests: empty registry raises
- [ ] Existing tests updated to expect `RuntimeError`
- [ ] No regression in 782 tests

## Also: Frontend Mock Removal (BLK-137)

I sent BLK-137 to frontend — `frontend/lib/api.ts` has mock data
arrays and every function silently fabricates success on failure.
This is the frontend equivalent of the stub mode: silent fake success
instead of real errors.

No action needed from you on BLK-137, but be aware that once frontend
removes the mocks, their app will start hitting your real endpoints
for the first time in every code path. Any 500s, any missing CORS
headers, any contract mismatches will surface immediately. Make sure
the API is stable.

## Resolution

BLK-138 complete. Stub mode removed from plan_node. Missing
dependencies now raise RuntimeError. Empty-registry check added
to build_tool_registry(). 3 new tests. 785 total tests pass.
