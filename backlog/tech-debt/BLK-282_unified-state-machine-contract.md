---
id: BLK-282
type: tech-debt
title: "Create a single canonical state machine contract for runs and UI transitions"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T11:40:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [state-machine, architecture, contract, ui, backend, maintenance]
---

## Description

The codebase currently has a fragmented state model spread across internal graph states, executor states, persisted run statuses, SSE events, and frontend UI states. The platform behaves as if it has a unified state chart, but there is no single canonical contract enforceable across layers.

This is a design debt issue, not just a bug: it leaves every layer free to invent its own interpretation of the same lifecycle, which creates drift and silent misclassification.

## Problem Statement

Multiple state machines are active at once:

- internal `RunStatus` values live in the agent graph
- execution context uses `queued`, `running`, `paused`, `completed`, `failed`, `cancelled`
- SSE emits `success`, `failed`, `cancelled`, `paused`, `max_iterations_reached`
- frontend uses a smaller UI state set with `idle`, `running`, `paused`, `completed`, `stopped`
- analytics and filtering treat anything with `completed` as success without state nuance

Without a single canonical state model, every layer chooses its own truth. This is the root pattern behind contract drift and false success reporting.

## Acceptance Criteria

- [ ] One state machine is documented and enforced across backend, persistence, SSE, and frontend
- [ ] All state transitions are explicit and named rather than inferred by ad hoc checks
- [ ] Terminal states are intentionally modeled and not flattened in a lossy way
- [ ] UI, analytics, and session history all consume the same contract
- [ ] A migration or compatibility layer exists for legacy run records

## Constraints

- Keep the runtime behavior mostly the same while making the contract explicit
- Do not introduce a second incompatible frontend-only state set
- Treat the canonical contract as the schema for all new data and events

## Dependencies

- Cross-cutting across backend runtime, SSE, store, frontend workbench, and analytics
- BLK-187, BLK-188, BLK-192, BLK-195, BLK-196

## Notes

- This is a system-level architecture debt item
- It explains many downstream reliability and trust problems rather than being a single bug itself

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
