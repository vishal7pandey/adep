---
id: BLK-100
type: bug
title: "Backend: _INJECTION_PATTERS typo — should be _INJECTION_PATTERNS"
priority: low
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, bug, typo, naming, stabilization]
---

## Bug

`src/agent/graph.py` line 904:

```python
_INJECTION_PATTERS = [
```

Should be `_INJECTION_PATTERNS` (missing `N`).

## Fix

Rename the constant. Update the reference on line 940.

## Acceptance Criteria

- [ ] Constant renamed to `_INJECTION_PATTERNS`
- [ ] All references updated
