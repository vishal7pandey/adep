---
id: BLK-257
type: bug
title: "Aggregate stats written non-atomically can corrupt daily budget tracking and 500 POST /runs"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T13:25:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [backend, budget, token-tracker, reliability, atomicity, concurrent]
---

## Description

`src/agent/token_tracking.py::_update_daily_stats` writes the running aggregate to `.adep/stats/aggregate.json` with a plain `write_text` (line ~227): read → mutate → full write, no temp file + atomic rename. `src/agent/budget.py:_load_daily_stats` then `json.loads` that file with **no fallback**. Under concurrency (BLK-224's threaded runs will call this from multiple workers) or a torn write/crash, the file can be mid-write or corrupt:

- A torn/corrupt `aggregate.json` makes `check_pre_run_budget` raise → `POST /api/v1/runs` returns 500 before any run can start.
- Interleaved read-modify-write between two workers can silently drop run counts/tokens from the aggregate (lost update).

## Problem Statement

Budget enforcement (BLK-050/051), the admin dashboard (BLK-052), and run-start checks all depend on this file. The write is not atomic and reads are not resilient; with parallelism this becomes a real data-loss + 500 surface. BLK-155 fixed this pattern for the main store; the stats file was missed.

## Acceptance Criteria

- [ ] Aggregate writes go through a temp file + `os.replace` (atomic on POSIX and Windows) or are serialized via a lock
- [ ] `_load_daily_stats` handles a missing/corrupt file gracefully (re-seed + warn, never raise in the pre-run path)
- [ ] A concurrency test: N parallel `_update_daily_stats` calls produce exactly N increments with no lost update
- [ ] A torn-write test: corrupt/mid-write file → budget check still succeeds

## Constraints

- Preserve the aggregate schema (BLK-120 dashboard consumes it)
- No global lock around the whole run loop

## Dependencies

- `src/agent/token_tracking.py`
- `src/agent/budget.py`
- Related BLK-224 (concurrent runs will exercise this path), BLK-155 (atomic store writes)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:25**: Filed from audit of stats write path and budget load-back, plus the race introduced by async concurrency work.