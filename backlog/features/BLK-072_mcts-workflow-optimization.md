---
id: BLK-072
type: feature
title: "MCTS workflow optimization — AFlow-style graph topology search"
priority: high
status: backlog
phase: 5
owner: unassigned
created: 2026-08-08T00:35:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-008, BLK-071]
tags: [ai, adas, mcts, aflow, workflow-optimization, graph, research]
---

## Description

Use Monte Carlo Tree Search (MCTS) to search the space of possible
agent workflow topologies. The system treats tool-calling nodes as
operators (Generate, Format, Review, Revise, Ensemble) and searches for
optimal graph structures.

## Motivation

From `agentic agent builder.md`: AFlow uses MCTS to navigate an
infinite structural space of code-represented graphs, guaranteeing
executable, structurally sound agents. This is a powerful way to
auto-optimize the ReAct graph.

## Design

**Operators:**
- `generate` — call LLM to produce a value
- `format` — reformat structured output
- `review` — validate a value against schema
- `revise` — retry extraction with different tool
- `ensemble` — combine multiple extraction attempts
- `verify` — deterministic invariant check
- `crop` — geometry tool
- `ocr` / `vlm` — perception tool

**Graph nodes:** each is a (tool, prompt_template, condition) tuple

**MCTS phases:**
1. **Selection:** pick candidate node by UCB1 score
2. **Expansion:** meta-LLM proposes code modifications or new edges
3. **Evaluation:** run the workflow on validation docs, measure
   accuracy, tokens, latency
4. **Backpropagation:** update selection probabilities

**Output:**
- Optimized graph as a LangGraph-compatible node/edge definition
- Utility score: `0.6 * accuracy - 0.3 * log(cost) - 0.1 * latency`

**API:**
```
POST /api/v1/skills/{id}/optimize
{
  "algorithm": "mcts",
  "iterations": 100,
  "validation_documents": [...]
}
```

## Acceptance Criteria

- [ ] `POST /api/v1/skills/{id}/optimize` with MCTS
- [ ] Operator library defined
- [ ] Node/edge expansion algorithm
- [ ] Validation execution on sample docs
- [ ] Backpropagation of utility scores
- [ ] Output: optimized graph definition
- [ ] Test: MCTS finds a better workflow than the baseline
- [ ] Test: evaluation uses mocked tools to control cost

## Constraints

- v1: limited to the existing tool set (no new tool invention)
- Search is offline on validation documents
- Budget cap to avoid expensive rollouts
- Requires ground truth or Surrogate Verifier for evaluation

## Dependencies

- BLK-008 (ReAct graph)
- BLK-071 (GEPA — shares evaluation harness)

## Notes

- `agentic agent builder.md`: AFlow, MetaAgent FSM generation
- OneFlow (BLK-074) may offer a cheaper baseline
