---
id: BLK-290
type: tech-debt
title: "Grounding and evidence trails are not first-class artifacts, increasing hallucination risk"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T11:10:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [grounding, evidence, audit, hallucination, traceability, anti-agentic]
---

## Description

The system emits traces, tool calls, and token summaries, but it does not consistently preserve the evidence needed to justify a field value or a final outcome. Grounding is fragmented across trace entries, partial extraction, and runtime state, with weak invariants for whether a result has real evidence behind it.

This is a major anti-agentic issue: the system behaves like an agent with memory and execution traces, but it still lacks a robust evidence contract for whether a field is actually grounded or just plausible.

## Problem Statement

Across the run lifecycle, the repo contains many signs of a weak evidence model:

- tool results are recorded in traces without consistent field-level grounding metadata
- status and analytics often erase the distinction between grounded and ungrounded values
- fallback outputs are allowed to masquerade as agentic outputs
- success metrics do not distinguish low-confidence or ungrounded completion from genuinely validated success
- the platform has logs and traces but not a single canonical evidence artifact per result

As a result, a user or reviewer cannot reliably answer: what evidence supports this extracted value, which tool produced it, and what validation path confirmed it?

## Acceptance Criteria

- [ ] Every extracted field has a canonical grounding/evidence record, not only a confidence score
- [ ] Results can be traced back to the specific tool and source region that supported them
- [ ] Metrics exclude ungrounded or fallback-only outputs from genuine success calculations
- [ ] A result should declare whether it is fully grounded, partially grounded, or ungrounded
- [ ] Observability and audit exports include evidence references for each final extracted value

## Constraints

- Keep the current trace model intact while adding missing evidence metadata
- Do not treat confidence alone as proof of grounding
- Preserve compatibility with historical runs that lack full evidence metadata

## Dependencies

- `src/agent/graph.py`
- `src/api/run_engine.py`
- `src/agent/guardrails/output_validation.py`
- `src/observability` stack
- BLK-178, and two tickets originally filed as BLK-191/BLK-192 that collided with other concurrently-filed tickets and were renumbered: "graph-extraction-runtime-does-not-use-graph-specific-validation-or-control-metrics" is now BLK-218, "hallucinated-success-through-fallback-bypass" is now BLK-219, "live-agent-collapses-multi-page-documents-to-a-single-page-handle" is now BLK-220, "false-success-through-status-mapping" is now BLK-221 — whichever pair this ticket meant, use the titles above to find the current IDs

## Notes

- This is the missing anti-hallucination infrastructure the project needs if it wants to claim grounded extraction rather than plausible output
- The platform has strong runtime plumbing but weak evidence semantics

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
