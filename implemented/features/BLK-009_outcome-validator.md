---
id: BLK-009
type: feature
title: "Outcome Validator (pragmatic gap-report generator)"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-001]
tags: [agent, validator, pragmatic, core]
---

## Description

Implement the Outcome Validator that checks the partial extraction against
the template and emits a structured GapReport. Code checks run first
(presence, type/format, math invariants, grounding, thresholds). Optional
semantic checks (LLM-assisted, structured prompts) may be enabled per-Skill
but are off by default. Don't build semantic checks until a real document
type proves they're needed [SF].

## Acceptance Criteria

- [ ] GapType enum (MISSING, TYPE_ERROR, LOW_CONFIDENCE, UNGROUNDED, INVARIANT_FAIL, SEMANTIC_FAIL)
- [ ] FieldGap and GapReport dataclasses
- [ ] ValidatorConfig with per-field threshold overrides
- [ ] validate_extraction(template, values, skill) -> GapReport
- [ ] Invariant support (e.g., subtotal + tax == total ± 0.01)
- [ ] FormatChecker for type/format validation (ISO date, numeric, enum)
- [ ] FieldGap includes `last_error` and `last_tool` fields for retry-loop prevention (§12.3)
- [ ] Optional semantic check hook (LLM-assisted, off by default)
- [ ] Unit tests covering all GapTypes and edge cases

## Constraints

- Pragmatic-first: code checks by default, LLM only for optional semantic checks (§4.1)
- Semantic checks are opt-in per-Skill, off by default [SF]
- Don't overengineer — build what's needed for Invoice, extend when a real
document type demands it

## Dependencies

- BLK-001 (FieldValue, Grounding types)

## Notes

- vision.md §4.1 (pragmatic-first validator)
- Existing `src/agent/validator.py` and `src/tests/test_validator.py` — refine
