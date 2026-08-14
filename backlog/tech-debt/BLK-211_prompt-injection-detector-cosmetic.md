---
id: BLK-211
type: tech-debt
title: "Prompt injection detection is cosmetic — logs but never blocks, and pattern list is trivially bypassable"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T12:30:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [security, prompt-injection, agent, dead-code, guardrails]
---

## Description

The prompt injection detection in `src/agent/graph.py` (`_contains_instruction_patterns`, `_INJECTION_PATTERNS`) is a 16-entry keyword list that checks for phrases like "ignore previous instructions", "you are now", "act as if", etc. The function's own docstring admits:

> "This is a detection/logging function, not a blocking function — the architecture itself prevents injection because the LLM output is always parsed as structured JSON."

The function is called in `plan_node` but only logs a warning — it never blocks, pauses, or modifies the agent's behavior. Additionally, the guardrails subsystem (`src/agent/guardrails/output_validation.py`) has a more robust `INSTRUCTION_PATTERNS` list with regex patterns, but that module is dead code (BLK-179).

## Problem Statement

- The injection detector is security theater — it logs but doesn't act, and logs are rarely monitored in real-time
- The 16-phrase keyword list is trivially bypassable: synonyms, non-English languages, obfuscation ("ign0re"), indirect instructions, or simply not using any of the exact phrases
- There are two separate injection pattern lists (`graph.py` and `output_validation.py`) that don't share entries or logic — the guardrails one is more comprehensive but dead, the graph one is live but weaker
- The docstring's claim that "the architecture itself prevents injection" is overstated — the LLM's structured JSON output still influences tool selection and field values, which can be manipulated through injection

## Acceptance Criteria

- [ ] Consolidate the two injection pattern lists into a single, shared module (preferably in `src/agent/guardrails/`)
- [ ] Either make the detector actionable (flag the trace, reduce confidence, trigger HITL review) or remove it and document that injection prevention is architectural (JSON parsing + validator)
- [ ] If keeping the detector, expand the pattern list significantly or use a proper classifier
- [ ] Add tests that verify the detector's behavior (currently only tested in `test_guardrails.py` which is dead code)

## Constraints

- Don't over-engineer — a simple keyword list is fine if it's honest about what it does
- If making it actionable, coordinate with BLK-204 (HITL gate) since that's the natural place for injection-triggered review

## Dependencies

- `src/agent/graph.py` (`_INJECTION_PATTERNS`, `_contains_instruction_patterns`)
- `src/agent/guardrails/output_validation.py` (`INSTRUCTION_PATTERNS`) — dead code per BLK-179
- Related to BLK-179 (guardrails dead code) and BLK-183 (decorative prompt injection detector)

## Notes

- Found during full-repo audit; BLK-183 already partially covers this, but this item focuses on the duplication and the gap between the live (weak) and dead (stronger) implementations

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
