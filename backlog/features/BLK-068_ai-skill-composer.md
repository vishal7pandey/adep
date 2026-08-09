---
id: BLK-068
type: feature
title: "AI Skill Composer — generate skills from natural language and examples"
priority: high
status: backlog
phase: 5
owner: unassigned
created: 2026-08-08T00:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-029, BLK-070]
tags: [ai, adas, skill-composer, natural-language, evoskills, skillsmith, research]
---

## Description

A meta-agent that generates a Skill (system prompt, tool preferences,
probe order, invariants, failure actions) from a natural language
description and optional sample documents. The Skill Composer produces
a candidate playbook, then co-evolves it with a Surrogate Verifier
(BLK-070).

## Motivation

From `agentic agent builder.md`: the Skill Composer is the most
intricate module. It must generate multi-file skill artifacts and
co-evolve them through generate-verify-refine loops. This item creates
the initial generation step.

## Design

**Input:**
- Natural language description (e.g., "Extract fields from a commercial
  lease, focusing on rent escalation and CAM fee clauses")
- Target Template (already generated or selected)
- Optional: 1-3 sample documents
- Optional: existing skill to use as starting point

**Output:**
- `Skill` dataclass with:
  - `system_prompt`
  - `tool_preferences`
  - `probe_order`
  - `invariants`
  - `failure_actions`
  - `semantic_checks_enabled`
  - `semantic_prompt`

**Implementation:**
- LLM call with structured output
- Few-shot examples of well-formed skills
- GICS sector hint from description (optional)
- Generated skill reviewed by user before co-evolution

**UI:**
- "Auto-generate skill" button in Skill Editor
- Textarea for description
- Template selector
- Sample document upload (optional)
- Generated skill opens in editor for review

## Acceptance Criteria

- [ ] `POST /api/v1/skills/generate` accepts description + template and
      returns generated skill
- [ ] Frontend "Auto-generate" in Skill Editor
- [ ] Generated skill editable before save
- [ ] Tool preferences chosen from available tool registry
- [ ] Invariants generated based on field types
- [ ] Failure actions include sensible defaults (crop → VLM fallback)
- [ ] Test: NL description → skill with system prompt + 3+ tools

## Constraints

- v1: generated skill must be reviewed by human (HITL)
- No auto-evolution yet — that is BLK-070/071
- Sample docs optional and not deeply analyzed in v1

## Dependencies

- BLK-029 (Skill Editor)
- BLK-070 (Surrogate Verifier — for co-evolution)

## Notes

- `agentic agent builder.md`: Skill Composer uses EvoSkills /
  SkillSmith co-evolution patterns
- This item is the generator; BLK-070 is the verifier; BLK-071 is the
  evolutionary loop
