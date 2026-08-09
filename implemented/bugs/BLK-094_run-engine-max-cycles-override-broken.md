---
id: BLK-094
type: bug
title: "Backend: run_engine applies max_cycles override incorrectly — resets total_cycles to 0"
priority: medium
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, bug, run-engine, config, stabilization]
---

## Bug

`src/api/run_engine.py` lines 167-169:

```python
agent_config = def_data.get("agent_config", {})
if agent_config.get("max_cycles_per_document"):
    state["total_cycles"] = 0  # Reset; cap checked in reflect node
```

This code is supposed to apply a per-definition max cycles override,
but instead it **resets `total_cycles` to 0** (which is already 0
from `build_initial_state`). The actual override value is never
applied to any config that the reflect node checks.

The reflect node checks `settings.max_cycles_per_document` (global
config), not a per-definition override. So the definition's
`max_cycles_per_document` is silently ignored.

## Fix

Pass the override into the graph or validator config:

```python
# Apply definition overrides
agent_config = def_data.get("agent_config", {})
max_cycles = agent_config.get("max_cycles_per_document",
                               settings.max_cycles_per_document)

# Pass to graph via config
graph = build_react_graph(
    registry=registry,
    skill=skill,
    validator_config=validator_config,
    breaker=breaker,
    max_cycles_per_document=max_cycles,  # new param
)

# In build_react_graph, thread it to _check_caps or use config
```

Or simpler: use LangGraph's `recursion_limit` config:

```python
final_state = graph.invoke(
    state,
    config={"recursion_limit": max_cycles + 10},
)
```

## Acceptance Criteria

- [ ] Per-definition `max_cycles_per_document` override is respected
- [ ] Global `settings.max_cycles_per_document` used as default
- [ ] No silent reset of `total_cycles`
