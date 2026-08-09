---
id: BLK-095
type: bug
title: "Backend: reflect_node sets status to string 'paused' instead of RunStatus constant"
priority: medium
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, bug, graph, status, stabilization]
---

## Bug

`src/agent/graph.py` line 501:

```python
elif consecutive_non_improving >= 5:
    status = "paused"  # Auto-pause on trajectory critical [BLK-049]
```

`RunStatus` class (state.py line 337) defines:
`PLANNING`, `ACTING`, `OBSERVING`, `REFLECTING`, `COMPLETE`,
`PARTIAL`, `ERROR`.

There is **no `PAUSED` constant**. The string `"paused"` is used
directly. This causes inconsistency:

1. `should_continue` (line 700) checks for `RunStatus.COMPLETE`,
   `RunStatus.PARTIAL`, `RunStatus.ERROR` — it does NOT check for
   `"paused"`, so a paused run would route to `"plan"` instead of
   `"terminate"`, creating an infinite loop.
2. `map_status_to_frontend` (run_engine.py line 71) checks for
   `PLANNING`, `ACTING`, `OBSERVING`, `REFLECTING` → `"running"`,
   `COMPLETE` → `"completed"`, else → `"failed"`. A `"paused"`
   status would map to `"failed"`.

## Fix

1. Add `PAUSED = "paused"` to `RunStatus` class
2. Use `RunStatus.PAUSED` in reflect_node
3. Add `RunStatus.PAUSED` to `should_continue`'s terminal check
4. Add `RunStatus.PAUSED` to `map_status_to_frontend` → `"paused"`

```python
class RunStatus:
    # ... existing ...
    PAUSED = "paused"
```

```python
# should_continue
if status in (RunStatus.COMPLETE, RunStatus.PARTIAL,
              RunStatus.ERROR, RunStatus.PAUSED):
    return "terminate"
```

```python
# map_status_to_frontend
if status == RunStatus.PAUSED:
    return "paused"
```

## Acceptance Criteria

- [ ] `RunStatus.PAUSED` constant defined
- [ ] `should_continue` routes paused runs to terminate
- [ ] `map_status_to_frontend` returns "paused" for paused runs
- [ ] No infinite loop when trajectory critical triggers auto-pause
