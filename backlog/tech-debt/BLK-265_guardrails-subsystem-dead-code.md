---
id: BLK-265
type: tech-debt
title: "Guardrails subsystem (8 modules, ~2,140 lines) is dead code — not wired into the run pipeline"
priority: critical
status: backlog
phase: 1
owner: devin
created: 2026-08-09T10:05:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [guardrails, safety, security, dead-code, misleading-docs]
---

## Description

`src/agent/guardrails/` contains 8 modules (`audit_logging.py`, `exfiltration_prevention.py`, `hallucination_detection.py`, `loop_detection.py`, `output_validation.py`, `pii_redaction.py`, `retry_circuit_breaker.py`, `tool_guardrails.py`, ~2,140 lines total). A full cross-reference of every production module in `src/` against every other file confirms: **all 8 files are imported by nothing except their own unit tests.** `src/agent/graph.py`, `src/api/run_engine.py`, `src/api/run_executor.py`, `main.py`, and every route file have zero references to `src.agent.guardrails`.

The package docstring states:

> "No single guardrail is the last line of defense... Every output is validated, sanitized, and audited before it reaches tool execution or state mutation."

This claim is false for the running system. It is only true inside the guardrails package's own unit tests, which call the functions directly and never go through the actual pipeline.

## Problem Statement

This is worse than simply having no guardrails: a code reviewer or a future engineer/AI session grepping the repo for "do we have PII redaction / loop detection / audit logging / exfiltration prevention" will find a confident, well-documented "yes" — passing tests included — and reasonably conclude protections exist that do not affect any real run. This is a trust/safety-review risk, not just unused code.

Verified still true as of 2026-08-09 (`grep -rn "guardrails" src --include="*.py"` outside the package and its tests returns zero hits).

## Acceptance Criteria

- [ ] Decision made and documented: wire the guardrails into the real pipeline (`plan_node`/`act_node`/`observe_node` in `src/agent/graph.py`) or remove the package
- [ ] If wired: each of the 8 modules has at least one call site in the actual run path, and an integration test proves it runs during `execute_run()`, not just unit-level
- [ ] If removed: package deleted, and any accurate/still-relevant claims are moved into whatever mechanism actually provides them (e.g. real circuit breaker in `graph.py`, real injection-pattern logging in `_contains_instruction_patterns`)
- [ ] Package docstring (or its replacement) makes no claims about protections that don't run in production
- [ ] `.adep`/README/vision docs that reference guardrails are updated to match reality

## Constraints

- This needs a decision, not a mechanical cleanup — evaluate whether each guardrail (PII redaction, exfiltration prevention, hallucination detection, loop detection, output validation, tool guardrails, audit logging, circuit breaker) is still wanted before wiring or deleting
- If wiring, be mindful of the existing (real, live) `CircuitBreaker` in `graph.py` — see BLK-180, do not create a third circuit breaker implementation

## Dependencies

- `src/agent/graph.py` (`plan_node`, `act_node`, `observe_node`)
- `src/agent/guardrails/*`
- BLK-180 (duplicate circuit breaker) — resolve together if guardrails' `retry_circuit_breaker.py` is kept

## Notes

- Found via full-repo audit (`ADE_codebase_audit.md`, §2); this is a re-confirmation, not a new finding — flagged there as the second-highest-priority item after the fallback bypass (BLK-178)
- `src/eval/accuracy.py` and `src/eval/benchmarks.py` show the same "built to spec, tested in isolation, never wired to anything runnable" pattern at lower stakes — tracked separately in BLK-182

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T10:05 (mgmt)**: Logged after re-running the cross-reference scan; zero non-test call sites confirmed across `src/`.
