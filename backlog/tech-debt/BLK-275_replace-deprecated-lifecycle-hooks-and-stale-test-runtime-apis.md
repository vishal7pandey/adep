---
id: BLK-275
type: tech-debt
title: "Replace deprecated FastAPI lifecycle hooks and stale test/runtime APIs"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T10:35:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [platform, dependencies, fastapi, testing, deprecation, maintenance]
---

## Description

A test collection pass on August 9, 2026 collected 1,302 tests successfully but emitted deprecation warnings from the runtime and test stack. None of these warnings are emergency bugs, but they are real platform debt that will eventually turn into breakage as dependencies move forward.

## Problem Statement

Current signals include:

- `src/api/main.py` still uses `@app.on_event("startup")` and `@app.on_event("shutdown")`, both deprecated in FastAPI in favor of lifespan handlers
- the test stack warns about `starlette.testclient` / `httpx` compatibility churn
- LangGraph checkpoint serialization emits a pending deprecation warning around `allowed_objects`

Leaving these unaddressed increases the odds of:

- dependency upgrades breaking app startup/shutdown semantics
- test harness churn turning into noisy or failing CI
- future upgrades being harder because multiple migrations pile up

## Acceptance Criteria

- [ ] Migrate FastAPI startup/shutdown logic to lifespan handlers
- [ ] Pin or upgrade the test stack to remove known deprecation warnings intentionally
- [ ] Audit LangGraph checkpoint serializer configuration and set explicit options where required
- [ ] Test collection and normal smoke tests run without avoidable deprecation noise
- [ ] Dependency decisions are documented so future upgrades have a clear baseline

## Constraints

- Keep current async executor startup and shutdown behavior unchanged from the user’s perspective
- Avoid broad dependency churn unrelated to these warnings
- Treat this as a focused cleanup, not a framework migration project

## Dependencies

- Likely touches `src/api/main.py`, test dependencies, and LangGraph configuration points

## Implementation Log

- **2026-08-09T16:00 (mgmt)**: Reassigned from `cline` (mandate suspended, see projectmgmt/STATUS.md 2026-08-09 16:00 note) to `devin`. Test-code ownership for this file's domain reverts to the implementing team; independent verification now happens via cross-team review (devin<->antigravity) instead of a dedicated gate.

- **2026-08-09 (mgmt)**: Assigned to `cline` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
