---
id: BLK-204
type: tech-debt
title: "src/agent/hitl.py is unwired dead code — BLK-047 marked implemented but gate never fires"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T11:55:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [dead-code, hitl, agent, process, backlog-integrity]
---

## Description

`src/agent/hitl.py` (100 lines) implements risk tier classification for a Human-in-the-Loop (HITL) gate pattern. It defines `RiskTier` (LOW/MEDIUM/HIGH/CRITICAL), `GateDecision`, and `classify_extraction_risk()`.

The module is **not imported** by any production code path:
- `src/api/run_engine.py` — no import of `hitl` or `classify_extraction_risk`
- `src/agent/graph.py` — no import of `hitl`
- `src/api/routes/runs.py` — no import of `hitl`
- `src/api/main.py` — no import of `hitl`

It is only imported by its own test (`src/tests/test_hitl.py`).

Meanwhile, `BLK-047_hitl-gate-pattern.md` sits in `backlog/implemented/features/` — marked as **implemented**.

## Problem Statement

- The HITL gate was marked as "implemented" but the gate never fires during a run — `classify_extraction_risk()` is never called
- The agent can terminate with partial results (PARTIAL status) without any human review gate, even though the code defines a CRITICAL risk tier for exactly this scenario
- This is the fourth instance of the "code exists but isn't wired in" pattern (after guardrails BLK-179, eval modules BLK-182, and AI modules BLK-199)
- The backlog says this is done; the reality is it's dead code with tests that prove the dead code works in isolation

## Acceptance Criteria

- [ ] Either wire `classify_extraction_risk()` into the run lifecycle (call it before returning partial/failed results, expose gate decisions via SSE, add frontend approval UI) and keep BLK-047 in `implemented/`, or move BLK-047 back to `features/` and acknowledge the implementation is incomplete
- [ ] If wiring in: the gate should fire in `terminate_node` or `_execute_run_inner` when status is PARTIAL or ERROR, emit a SSE event for the gate decision, and pause the run until human approval/rejection
- [ ] If not wiring in: update BLK-047 status to reflect reality and document why the feature was abandoned after implementation

## Constraints

- Wiring in HITL is a significant feature — it requires frontend UI, SSE events, and run lifecycle changes
- Don't leave the code in limbo

## Dependencies

- `src/agent/hitl.py`
- `backlog/implemented/features/BLK-047_hitl-gate-pattern.md`
- Related to BLK-179 (guardrails dead code), BLK-182 (eval unwired), BLK-199 (AI modules unwired) — same systemic pattern

## Notes

- Found during full-repo audit; this is the fourth instance of the same pattern, indicating a systemic process issue where features are implemented and marked done without integration

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
