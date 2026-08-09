---
id: BLK-071
type: feature
title: "Reflective Prompt Evolution (GEPA) — optimize skills by reflecting on traces"
priority: high
status: backlog
phase: 5
owner: unassigned
created: 2026-08-08T00:35:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-068, BLK-070]
tags: [ai, adas, gepa, prompt-evolution, optimization, skill-improvement, research]
---

## Description

Implement the GEPA (Genetic-Pareto) reflective prompt evolution loop
for skills. The system samples a skill's execution trajectories,
invokes a reflective LLM to diagnose failures and propose textual
prompt updates, and applies Pareto-optimal genetic mutations to
create improved skill variants.

## Motivation

From `agentic agent builder.md`: GEPA outperforms GRPO by ~10% (up to
20% on complex math) while requiring 35x fewer rollouts. This is a far
more efficient way to optimize skills than reinforcement learning.

## Design

**Loop:**
1. Run skill on N sample documents
2. Collect full trajectory (thoughts, tool calls, outputs, gap reports)
3. Reflective LLM analyzes trajectories and proposes prompt updates
4. Mutate prompts: combine, cross-pollinate, small edits
5. Evaluate each variant on the same sample docs
6. Select Pareto-optimal variants (accuracy vs. cost)
7. Repeat for M generations

**Prompts to optimize:**
- Skill `system_prompt`
- Probe order rationale strings
- Failure action rationale strings
- Semantic check prompt

**Outputs:**
- Best skill variant
- Pareto frontier of variants
- Report: accuracy, cost, latency per generation

**API:**
```
POST /api/v1/skills/{id}/evolve
{
  "generations": 5,
  "population_size": 8,
  "sample_documents": [...]
}
```

**UI:**
- "Evolve Skill" button in Skill Editor
- Shows progress: generation N, best score
- Pareto frontier chart (accuracy vs. cost)
- User selects best variant or keeps original

## Acceptance Criteria

- [ ] `POST /api/v1/skills/{id}/evolve` endpoint
- [ ] Reflective LLM diagnosis of traces
- [ ] Prompt mutation operators
- [ ] Pareto selection
- [ ] N-generation loop
- [ ] Frontend "Evolve" button + progress UI
- [ ] Pareto frontier visualization
- [ ] Test: skill accuracy improves after 3 generations
- [ ] Test: evolution uses fewer rollouts than random search

## Constraints

- v1: requires sample documents with known ground truth (or uses
  Surrogate Verifier for scoring)
- Evolution is offline, not during a production run
- Cost budget enforced to prevent runaway evolution

## Dependencies

- BLK-068 (AI Skill Composer)
- BLK-070 (Surrogate Verifier)

## Notes

- `agentic agent builder.md`: GEPA = major breakthrough over RL
- Alternative: DSPy (BLK-073) or TextGrad
