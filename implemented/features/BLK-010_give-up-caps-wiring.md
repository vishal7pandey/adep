---
id: BLK-010
type: feature
title: "Wire give-up caps into ReAct graph conditional edges"
priority: medium
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-008, BLK-009]
tags: [agent, safety, give-up, caps]
---

## Description

Wire the per-field and per-document cycle caps into the ReAct graph's
conditional edges. When either cap is hit, the graph transitions to
terminate with a partial result and explicit gaps — never an infinite loop,
never a fabricated fill. Also wire the provider-level circuit breaker: if a
provider fails repeatedly across multiple calls in a single run, subsequent
calls return `provider_unavailable` immediately (§2.7).

## Acceptance Criteria

- [ ] Per-field cycle cap enforced (ADE_MAX_CYCLES_PER_FIELD, default 5)
- [ ] Per-document cycle cap enforced (ADE_MAX_CYCLES_PER_DOCUMENT, default 30)
- [ ] Provider circuit breaker: N failures → provider_unavailable for rest of run (§2.7)
- [ ] On cap exhaustion: terminate with partial result + GapReport
- [ ] On provider unavailable: agent falls back to alt provider or terminates with gaps
- [ ] `provider_errors` list included in ExtractedResult
- [ ] Caps and circuit breaker threshold are config-driven (from Settings)
- [ ] Unit test verifying termination on cap exhaustion
- [ ] Unit test verifying circuit breaker trips after N provider failures

## Constraints

- A failed extraction is a structured object, not an exception (§2.6)
- Provider failures are structured ToolResult(ok=False), not exceptions (§2.7)

## Dependencies

- BLK-008 (ReAct graph)
- BLK-009 (Validator produces GapReport)

## Notes

- vision.md §2.6 (give-up threshold), §2.7 (provider failure and error propagation)
