---
id: BLK-278
type: tech-debt
title: "RunExecutor holds completed runs in memory indefinitely — unbounded growth"
priority: medium
status: backlog
phase: 5
owner: devin
created: 2026-08-09T11:15:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [backend, memory, scalability, ops]
---

## Description

`src/api/run_executor.py` `RunExecutor._runs` is a dict that accumulates every `RunContext` ever enqueued and never evicts completed runs:

```python
self._runs: dict[str, RunContext] = {}
```

`RunContext` holds:
- the SSE event emitter (`_queue` is an `asyncio.Queue` — it grows with buffered events)
- `event_buffer` (list of all SSE events)
- `result` (full serialized result payload)

There is no retention bound on `_runs`. In a long-running server (batch processing, BLK-118), the executor's memory usage grows monotonically with every run, eventually causing OOM. Even with modest traffic, a few hundred runs × buffered events × full result can exhaust RAM.

## Acceptance Criteria

- [ ] Add a retention policy to `RunExecutor._runs` (e.g. keep last N completed runs, or TTL by age)
- [ ] Evict completed/failed/cancelled runs older than a configurable TTL, or cap count
- [ ] Add a test that verifies eviction when the cap is exceeded
- [ ] Document the retention policy in `config.py` (e.g. `ade_executor_retention_count` or TTL seconds)

## Constraints

- Must not break the ability to `GET /runs/{id}` after a run completes — the run data is already persisted to the store (`_persist_run`), so eviction from memory is safe
- In-flight and queued runs must never be evicted

## Dependencies

- None

## Notes

- Found during async run executor audit (BLK-129)
- `RunContext.to_dict()` is already persisted to the file store, so memory eviction is safe
- Related to BLK-118 (batch queue) which will increase steady-state volume

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
