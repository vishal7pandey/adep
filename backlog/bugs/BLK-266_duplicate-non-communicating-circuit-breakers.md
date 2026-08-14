---
id: BLK-266
type: bug
title: "Two separate, non-communicating circuit breakers; the live one is keyed by tool name, not provider"
priority: medium
status: backlog
phase: 1
owner: devin
created: 2026-08-09T10:10:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [resilience, circuit-breaker, agent, dead-code]
---

## Description

There are two independent circuit breaker implementations in the codebase:

- `CircuitBreaker` in `src/agent/graph.py` (~lines 58-70) — the real one, instantiated in `run_engine.py` with `threshold=3` and wired into `act_node`. This is the one that actually protects live runs.
- `GlobalCircuitBreaker` in `src/agent/guardrails/retry_circuit_breaker.py` (344 lines) — dead code, part of the unwired guardrails package (BLK-179).

They share no state and can't see each other's failures.

Separately, the live `CircuitBreaker.is_tripped(tool_name)` / `record_failure(tool_name)` is keyed by **tool name**, even though its class docstring describes it as a "per-provider" breaker. If two different tools front the same underlying provider (e.g. an OCR tool and a table-detection tool both hitting the same Azure OCR endpoint), a failure storm on one tool won't trip the breaker for the other — so a provider that's actually down keeps getting hit through its other tool, and the resilience guarantee the docstring implies doesn't hold.

## Acceptance Criteria

- [ ] Resolve the duplication: either delete `GlobalCircuitBreaker` (if guardrails is deleted per BLK-179) or consolidate on one implementation used everywhere
- [ ] The live breaker's docstring and its actual keying (tool vs. provider) are made consistent — either key it by provider identity, or correct the docstring to say "per-tool"
- [ ] If keying by provider: tools that share a backing provider (e.g. multiple Azure OCR/VLM tools) trip together on a failure storm
- [ ] Add/extend a test that exercises this: two tools on the same provider, one fails repeatedly, assert the other is correctly tripped (if provider-keyed) or correctly independent (if tool-keyed is the intended, documented behavior)

## Constraints

- Resolve alongside BLK-179 (guardrails wire-or-delete decision) since `GlobalCircuitBreaker` lives inside that package
- Don't change breaker behavior for tools that don't share a provider — this should only affect the failure-attribution granularity, not the threshold/backoff logic itself

## Dependencies

- `src/agent/graph.py` (`CircuitBreaker`, `act_node`)
- `src/agent/guardrails/retry_circuit_breaker.py` (`GlobalCircuitBreaker`) — see BLK-179
- `src/providers/` (provider-to-tool mapping needed if switching to provider-keyed)

## Notes

- Found via full-repo audit (`ADE_codebase_audit.md`, §3); confirmed still present as of 2026-08-09 — both classes exist, `GlobalCircuitBreaker` still has zero non-test call sites
- Low effort, low risk — reasonable to batch with the BLK-178 fallback fix since both touch `run_engine.py`/`graph.py` in the same pass

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T10:10 (mgmt)**: Logged after confirming both classes still exist independently and the live breaker is still tool-keyed.
