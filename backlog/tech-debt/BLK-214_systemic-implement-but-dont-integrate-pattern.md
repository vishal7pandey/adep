---
id: BLK-214
type: tech-debt
title: "Systemic 'implement but don't integrate' pattern — 5 subsystems with code, tests, and 'implemented' backlog status but zero production wiring"
priority: high
status: backlog
phase: 2
owner: mgmt
created: 2026-08-09T12:45:00+05:30
started: null
completed: null
estimate: L
depends-on: []
tags: [process, backlog-integrity, dead-code, architecture, systemic]
---

## Description

This is a meta-item documenting a systemic pattern across the ADEP codebase. Four separate subsystems have been implemented with full code, tests, and backlog items marked as "implemented" — but none are actually wired into the production execution path:

1. **Guardrails** (BLK-079 through BLK-086, BLK-179): 8 modules in `src/agent/guardrails/` (~67KB), imported only by their own tests. Not wired into `graph.py` or `run_engine.py`.

2. **HITL Gate** (BLK-047, BLK-204): `src/agent/hitl.py` (100 lines), imported only by its own test. `classify_extraction_risk()` is never called during a run. The approve/reject API endpoints exist but are manual — no gate ever triggers automatically.

3. **Eval Infrastructure** (BLK-128, BLK-182, BLK-205): `src/eval/` (~36KB), imported only by tests and a standalone script. Not wired into CI or API.

4. **Prompt Injection Detection** (BLK-043, BLK-183, BLK-211): Live in `graph.py` but only logs — never blocks, pauses, or modifies behavior. The more robust version in `guardrails/output_validation.py` is dead code.

Note: BLK-067 (AI Template Composer) and BLK-070 (Surrogate Verifier) were initially included in this list but were found to be properly wired to API endpoints and frontend UI. Their only issue is backlog status drift (BLK-199).

## Problem Statement

This is not four independent bugs — it's a **process failure**. The pattern is consistent:

1. A backlog item is created for a feature
2. The feature is implemented in isolation (module + tests)
3. The backlog item is moved to `implemented/` without integration
4. No one notices because CI only runs unit tests (which test the module in isolation), not integration tests that verify the feature is actually used
5. The feature appears "done" in the backlog but is dead code in production

This means:
- The backlog's "implemented" status is unreliable for at least 4 features
- ~110KB of code is dead weight that must be maintained, reviewed, and understood
- The project's claimed capabilities (guardrails, HITL, eval benchmarks, injection defense) are overstated
- New developers will waste time trying to understand how these features work, only to discover they don't

## Acceptance Criteria

- [ ] Conduct a full audit of all `backlog/implemented/` items and cross-reference each with actual production code wiring
- [ ] For each unwired "implemented" item: either wire it in and verify integration, or move it back to `features/` with a note explaining the gap
- [ ] Add a CI check that greps for modules only imported by their own tests (dead code detection)
- [ ] Update `projectmgmt/PROCESS.md` to require an "integration verified" step before moving items to `implemented/`
- [ ] Add integration tests that exercise the full run path and verify these subsystems are actually called

## Constraints

- This is a process fix, not a code fix — the individual wiring tasks are tracked in BLK-179, BLK-204, BLK-205, and BLK-211
- Don't delete any code — the implementations may be valuable once wired in
- The process change should prevent this pattern from recurring

## Dependencies

- BLK-179 (guardrails dead code)
- BLK-204 (HITL unwired)
- BLK-205 (eval modules unwired)
- BLK-211 (prompt injection cosmetic)
- `projectmgmt/PROCESS.md`
- `projectmgmt/STATUS.md`

## Notes

- Found during full-repo audit; this is the single most damaging process issue in the project. The backlog cannot be trusted, which undermines all project management. This is the same conclusion reached in `ADE_codebase_audit.md` §6 and BLK-161, but this item frames it as a systemic pattern rather than individual instances.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `mgmt` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
