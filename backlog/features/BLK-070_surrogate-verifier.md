---
id: BLK-070
type: feature
title: "Surrogate Verifier — information-isolated skill evaluator"
priority: high
status: assigned
phase: 5
owner: backend
created: 2026-08-08T00:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-008, BLK-009]
tags: [ai, adas, verifier, evoskills, validation, skillsmith, research]
---

## Description

Build a Surrogate Verifier that evaluates a generated skill's execution
trace and generates diagnostic signatures without requiring ground-truth
labels. Used by the AI Skill Composer (BLK-068) in a co-evolution loop.

## Motivation

From `agentic agent builder.md`: the Skill Composer couples a Skill
Generator with an information-isolated Surrogate Verifier. The verifier
independently evaluates execution traces and generates test assertions,
driving skill refinement without human-labeled data.

## Design

**Input:**
- Generated Skill
- Execution trace from a sample document
- Gap report
- Extracted output

**Output:**
- Diagnostic report:
  ```json
  {
    "diagnoses": [
      {"type": "tool_selection", "severity": "high", "message": "Used OCR on a region better suited for VLM"},
      {"type": "invariant", "severity": "medium", "message": "Missing date comparison invariant for due_date"}
    ],
    "proposed_tests": [
      {"assertion": "total_amount == sum(line_items.total) + tax_amount", "reason": "math invariant"}
    ],
    "skill_patch": {...}
  }
  ```

**Implementation:**
- LLM prompt: "You are an expert verifier. Given this skill and trace,
  find weaknesses and propose fixes. Do not use ground truth."
- Analyzes:
  - Tool selection patterns
  - Probe order efficiency
  - Missing invariants
  - Failure action coverage
  - Common failure signatures
- Proposes concrete skill patches

**Integration:**
- `POST /api/v1/skills/{id}/verify` runs the skill on sample docs,
  then calls Surrogate Verifier
- Returns diagnostic report
- Skill Composer uses this in generate-verify-refine loop (BLK-071)

## Acceptance Criteria

- [ ] Surrogate Verifier endpoint `POST /api/v1/skills/{id}/verify`
- [ ] Analyzes trace without ground truth
- [ ] Produces diagnoses + proposed tests + skill patches
- [ ] Identifies missing invariants
- [ ] Identifies inefficient tool selection
- [ ] Test: generated skill with missing date invariant → verifier flags it
- [ ] Test: skill using OCR on a poor-quality region → verifier suggests VLM

## Constraints

- v1: no access to ground-truth labels — purely trace-based
- Verifier is information-isolated from generator (no shared state)
- Diagnostics are suggestions, not auto-applied

## Dependencies

- BLK-008 (ReAct graph)
- BLK-009 (Outcome Validator)

## Notes

- `agentic agent builder.md`: Surrogate Verifier = key to co-evolution
- EvoSkills / SkillSmith pattern
