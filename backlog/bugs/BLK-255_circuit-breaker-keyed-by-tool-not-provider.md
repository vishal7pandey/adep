---
id: BLK-255
type: bug
title: "CircuitBreaker is keyed by tool name while its docstring claims per-provider protection — provider resilience is weaker than documented"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T13:15:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-180]
tags: [backend, circuit-breaker, providers, reliability, resilience]
---

## Description

The live `CircuitBreaker` in `src/agent/graph.py` (~lines 58-70, `is_tripped(tool_name)` / `record_failure(tool_name)`) is keyed by **tool name**, but its docstring describes it as a per-provider breaker. When two tools front the same underlying provider (e.g. an OCR tool and a table-detection tool both hitting the same Azure OCR/endpoint), a failure storm on one does not trip the breaker for the other. The resilience story is weaker than the docstring implies.

This overlaps BLK-180 (two non-communicating circuit breakers — the guardrails `GlobalCircuitBreaker` is dead). Here the *live* breaker still has the wrong keying granularity.

## Problem Statement

- Breaker effectiveness depends on sharing trip state across tools that share a flaky provider.
- The threshold (3) is right, but the breaker key should be a provider/endpoint identity (from tool metadata / provider config), not tool name.
- When a provider starts failing, all its tools should open; today only the exact failing tool trips, allowing the agent to waste cycles calling the others.

## Acceptance Criteria

- [ ] `CircuitBreaker` keying uses a provider-scoped identity (e.g. OCR vs VLM vs geometry) derived from each tool's backing provider rather than tool name
- [ ] Failing one tool in a provider family trips the breaker for the whole family
- [ ] A unit test: tool A and tool B share a provider; A fails 3x → both A and B report tripped
- [ ] Update the class docstring to match keying semantics (provider-scoped)
- [ ] Keep the original tool-name headline in logs/telemetry for observability

## Constraints

- Do not conflate unrelated providers by a naive prefix; map deterministically in the registry metadata
- Ties closely to provider abstraction in `src/providers/`

## Dependencies

- `src/agent/graph.py` CircuitBreaker
- `src/tools/` (provider metadata)
- Related BLK-180 (dead duplicate breaker), BLK-178

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:15 (mgmt)**: Filed after reading the live breaker keying vs its docstring.
