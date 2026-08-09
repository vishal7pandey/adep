---
id: BLK-096
type: bug
title: "Backend: AgentState missing document_state, consecutive_non_improving, token_usage, total_tokens, total_cost_usd in build_initial_state"
priority: medium
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, bug, state, initialization, stabilization]
---

## Bug

`src/run.py` `build_initial_state` (lines 81-98) does not initialize
several keys that are declared in `AgentState` (state.py lines
326-330) and read by graph nodes:

| Key | Declared in AgentState | Initialized in build_initial_state | Read by |
|-----|----------------------|-----------------------------------|---------|
| `document_state` | line 326 | ❌ missing | plan_node (multi-page nav) |
| `consecutive_non_improving` | line 327 | ❌ missing | reflect_node line 465 |
| `token_usage` | line 328 | ❌ missing | plan_node line 186, compact_node line 597 |
| `total_tokens` | line 329 | ❌ missing | plan_node line 187, compact_node line 598 |
| `total_cost_usd` | line 330 | ❌ missing | plan_node line 188, compact_node line 599 |

These keys use `state.get("key", default)` so they won't crash, but
the defaults may not be correct. For example, `consecutive_non_improving`
defaults to `0` via `.get()`, which is correct. But `token_usage`
defaults to `[]` via `.get()`, then `list()` is called on it — if
LangGraph doesn't merge the key, it stays missing every cycle.

More critically, `document_state` is never initialized for multi-page
documents. The `DocumentState` class exists but `build_initial_state`
always creates a single-page `DocumentHandle` without a
`DocumentState`.

## Fix

Add missing keys to `build_initial_state`:

```python
return AgentState(
    document=handle,
    template_schema=template,
    skill_name=skill.name,
    regions={},
    extraction={},
    trace=[],
    step=0,
    field_attempts={},
    total_cycles=0,
    status=RunStatus.PLANNING,
    attempted={},
    provider_errors=[],
    compaction_summary="",
    _planned_action=None,
    _tool_result=None,
    _compact_requested=False,
    # Missing keys:
    document_state=DocumentState.from_page_count(handle.pages),
    consecutive_non_improving=0,
    token_usage=[],
    total_tokens=0,
    total_cost_usd=0.0,
)
```

## Acceptance Criteria

- [ ] All AgentState keys initialized in `build_initial_state`
- [ ] `document_state` created with correct page count
- [ ] No `KeyError` or `.get()` default fallback needed in graph nodes
