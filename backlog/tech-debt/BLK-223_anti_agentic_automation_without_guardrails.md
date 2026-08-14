---
id: BLK-223
type: tech-debt
title: "Anti-agentic automation: confidence-driven execution without explicit guardrails and operator control"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T11:15:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [anti-agentic, guardrails, audit, operator-control, risk, hallucination]
---

## Description

The project has many agentic concepts in its architecture — planning, tools, reflection, circuit breakers, HITL gates — but the runtime still contains broad automation paths that continue without explicit operator control, without clear stopping conditions, and without consistent guardrail enforcement.

This is anti-agentic in the sense that the system looks autonomous while still lacking the discipline needed for safe execution. It can continue, silently substituting cheap outputs for real reasoning, and still present itself as a robust agent system.

## Problem Statement

The codebase shows repeated patterns where:

- a fallback is silently used when the agent should have stopped or raised a config error
- status mapping hides the actual outcome from the operator
- partial results are treated as the same as complete ones
- loops can continue beyond sensible limits without a meaningful human decision point
- metrics are computed from the wrong truth source, masking the actual run quality

This creates a high risk of overtrust in an automation pipeline that still lacks explicit guardrails and audit semantics. The platform may feel autonomous, but the operator can no longer tell what actually happened or whether the result is trustworthy.

## Acceptance Criteria

- [ ] Operator-visible run states expose meaningful outcomes: success, partial, failed, cancelled, paused, waiting for input
- [ ] Explicit stop/continue/override gates exist for partial runs and low-confidence outputs
- [ ] Auto-continue or fallback behaviors require a visible policy decision, not silent execution
- [ ] A risk classification is computed from evidence quality, not only from confidence or completion status
- [ ] Guardrail failures are surfaced as first-class run outcomes with operator instructions, not hidden in logs

## Constraints

- Do not treat “confidence > threshold” as equivalent to “safe to proceed”
- Keep operator controls explicit and understandable
- Preserve the autopilot notion for local/dev use but require evidence-coded boundaries in production-like settings

## Dependencies

- `src/agent/graph.py`
- `src/api/run_executor.py`
- `src/api/run_engine.py`
- guardrails modules and human-in-the-loop flow
- BLK-178, BLK-184; plus tickets originally filed as BLK-191/BLK-192/BLK-193 that collided with other concurrently-filed tickets and were renumbered: "graph-extraction-runtime-does-not-use-graph-specific-validation-or-control-metrics" is now BLK-218, "hallucinated-success-through-fallback-bypass" is now BLK-219, "live-agent-collapses-multi-page-documents-to-a-single-page-handle" is now BLK-220, "false-success-through-status-mapping" is now BLK-221, "grounding-and-evidence-audit-gap" is now BLK-222 — whichever set this ticket meant, use the titles above to find the current IDs

## Notes

- This item captures the broader governance problem behind many of the more specific bugs
- The system currently has the language of autonomy but not the discipline of safe, auditable autonomy

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
