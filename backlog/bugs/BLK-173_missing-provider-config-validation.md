---
id: BLK-173
type: bug
title: "Missing provider-config validation causes silent zero-output failures"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T09:15:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [config, providers, validation, reliability, zero-output]
---

## Description

The backend accepts empty or partially configured provider credentials and continues into a run without failing fast. In practice this can create zero-token or zero-field runs that look successful in the UI even though the agent never actually executed a meaningful extraction path.

This is the same class of problem called out in `vision.md §2.7` (provider failure and error propagation) and in the current backlog bug `BLK-171`. The system currently relies on downstream heuristics instead of a clear startup-time contract for provider readiness.

## Problem Statement

The settings model in `src/config.py` allows empty Azure values by default, and `run_executor.py` / `run_engine.py` may continue with partial state when provider configuration is missing. This creates three bad outcomes:

- silent zero-output execution
- misleading status values in the workbench
- difficult debugging because the root cause is hidden behind an empty run result

This is not a niche backend concern: it directly affects user trust, cost visibility, and the correctness of the run lifecycle.

## Acceptance Criteria

- [ ] Startup or run initialization fails fast when required provider config is missing
- [ ] Error messages clearly distinguish between "provider not configured" and "provider call failed"
- [ ] A run with missing provider config is never reported as completed without explicit failed state
- [ ] Frontend surfaces a clear actionable error instead of a blank or misleading success result
- [ ] Logs include provider identity, endpoint presence, and missing-field reason

## Constraints

- Must preserve graceful degradation for optional providers where the platform intentionally supports fallback
- Do not block local development runs that are intentionally offline unless they are actually invoked
- Validation should happen at config boundary and at run start; not only in a single downstream tool

## Dependencies

- BLK-171 (zero-token failure status bug)
- `src/config.py` settings contract
- provider adapter initialization in `src/providers/`

## Notes

- Related to `vision.md §2.7` and `§2.6`
- Mirrors the real-world issue where missing API keys can silently produce `0 tokens / 0 fields / status=completed`
- Current repo status flags this as a runtime reliability gap even though several status bugs have been resolved

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T09:15 (mgmt)**: Logged after reviewing config defaults, failure propagation rules, and the zero-token status bug pattern.
