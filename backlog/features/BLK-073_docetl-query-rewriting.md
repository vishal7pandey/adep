---
id: BLK-073
type: feature
title: "Agentic query rewriting — DocETL-style pipeline optimization"
priority: high
status: backlog
phase: 5
owner: unassigned
created: 2026-08-08T00:35:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-008, BLK-072]
tags: [ai, adas, docetl, query-rewriting, pipeline-optimization, research]
---

## Description

Implement DocETL-style agentic query rewriting. When an extraction
pipeline consistently fails on a class of documents (e.g., long-tail
edge cases like pet policy clauses in leases), the system automatically
rewrites the skill into smaller sub-tasks with validation.

## Motivation

From `agentic agent builder.md`: DocETL is an active pipeline optimizer
that decomposes extraction tasks and validates rewritten pipelines
against baselines, achieving up to 80% accuracy gains.

## Design

**Triggers for rewriting:**
- High failure rate on a field (>30% across sample docs)
- Semantic check failures concentrated in one area
- Validation failures of the same type

**Rewrite operations:**
- Decompose a monolithic field into sub-fields
- Map-reduce: extract per section, then aggregate
- Add intermediate verification steps
- Change probe order (e.g., VLM before OCR)
- Split table extraction into row-by-row then validate

**Validation:**
- Run original and rewritten pipelines on sample docs
- Compare accuracy and cost
- Keep the better pipeline
- If no improvement, reject and try another rewrite

**API:**
```
POST /api/v1/skills/{id}/rewrite
{
  "trigger": "field_failure_rate",
  "field": "pet_policy_clause",
  "sample_documents": [...]
}
```

**UI:**
- "Analyze & Rewrite" button in Skill Editor
- Shows detected failure patterns
- Proposed rewrites
- Before/after accuracy comparison
- User approves or rejects

## Acceptance Criteria

- [ ] `POST /api/v1/skills/{id}/rewrite` endpoint
- [ ] Detects common failure patterns
- [ ] Applies rewrite directives
- [ ] Validates rewritten vs baseline
- [ ] Decomposes complex fields into sub-tasks
- [ ] Map-reduce pattern for multi-section extraction
- [ ] Frontend "Analyze & Rewrite" button
- [ ] Test: rewrite improves accuracy on long-tail cases

## Constraints

- v1: human approval required before deploying rewrite
- Rewrites are constrained to the existing tool set
- No new primitives invented by the meta-agent

## Dependencies

- BLK-008 (ReAct graph)
- BLK-072 (MCTS — shares evaluation)

## Notes

- `agentic agent builder.md`: DocETL from UC Berkeley
- Complements GEPA and MCTS
