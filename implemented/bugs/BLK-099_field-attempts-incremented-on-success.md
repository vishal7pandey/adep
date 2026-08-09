---
id: BLK-099
type: tech-debt
title: "Backend: _process_tool_result increments field_attempts on success — should only increment on failure"
priority: medium
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, tech-debt, graph, field-attempts, stabilization]
---

## Bug

`src/agent/graph.py` lines 876-877:

```python
if field in field_attempts:
    field_attempts[field] = field_attempts.get(field, 0) + 1
```

This is inside `_process_tool_result`, which is called on
**successful** tool results (line 393). But `field_attempts` is
supposed to track **failed** attempts for give-up enforcement (§2.6).

Looking at the observe_node (line 372-373), failed tools already
increment `field_attempts`:

```python
if field:
    field_attempts[field] = field_attempts.get(field, 0) + 1
```

So field_attempts is incremented on **both** success and failure.
This means the give-up cap (`max_cycles_per_field`) is reached twice
as fast as intended — a field that succeeds on the 3rd attempt would
have `field_attempts[field] = 3` (1 from each failed attempt + 1
from the successful one), hitting the cap of 5 after only 2 failures
+ 3 successes.

## Fix

Remove the increment from `_process_tool_result` (lines 876-877).
Field attempts should only be counted on failure, which is already
handled in the `not result.ok` branch of `observe_node`.

## Acceptance Criteria

- [ ] `field_attempts` only incremented on failed tool calls
- [ ] Successful extractions don't consume give-up budget
- [ ] Give-up cap triggers at the correct failure count
