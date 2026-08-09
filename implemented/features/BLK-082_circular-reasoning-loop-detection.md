---
id: BLK-082
type: feature
title: "Circular reasoning & loop detection"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T01:45:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-049]
tags: [backend, security, guardrails, loop-detection, circular-reasoning, safety]
---

## Description

Detect when the agent is stuck in a loop — repeating the same tool calls,
visiting the same fields, or producing the same thoughts across cycles.
Terminate the run gracefully when a loop is detected.

## Motivation

LLMs can get stuck in repetitive loops: calling the same tool with the
same arguments, re-extracting the same field, or oscillating between two
states. This wastes tokens, burns budget, and never converges. Give-up
caps (§2.6) catch this eventually, but early detection is cheaper and
more informative.

## Guardrails

1. **Tool call repetition detection:** If the same tool is called with
   the same arguments for 3 consecutive cycles, terminate with
   `status: 'loop_detected'`.

2. **Field re-extraction limit:** If a field is re-extracted more than
   `max_cycles_per_field` (existing config, default 5) times without
   improvement in confidence, mark as `status: 'failed'` and move on.

3. **Thought similarity detection:** Compute cosine similarity of
   consecutive thought embeddings. If similarity > 0.95 for 3 consecutive
   thoughts, flag as circular reasoning and terminate.

4. **Oscillation detection:** If the agent alternates between two
   fields/states for > 4 cycles, terminate with `status: 'oscillation'`.

5. **No-progress detection:** If `extracted_fields_count` does not
   increase for `max_cycles_per_document / 3` cycles, terminate with
   `status: 'no_progress'`.

6. **Loop report:** When a loop is detected, the termination event
   includes: loop type, cycle range, repeated pattern summary.

## Acceptance Criteria

- [ ] Same tool+args for 3 cycles → terminate with `loop_detected`
- [ ] Field re-extraction capped at `max_cycles_per_field`
- [ ] Thought similarity > 0.95 for 3 cycles → terminate
- [ ] Oscillation between 2 states for 4 cycles → terminate
- [ ] No progress for configurable threshold → terminate
- [ ] Loop report included in termination event
- [ ] Unit tests: tool repetition, field re-extraction, thought loop

## Dependencies

- BLK-049 (trajectory integrity — shares cascade detection concepts)
