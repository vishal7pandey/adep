---
id: BLK-076
type: feature
title: "Dynamic cost estimator — predict extraction cost before running"
priority: low
status: backlog
phase: 5
owner: unassigned
created: 2026-08-08T00:35:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-050, BLK-059]
tags: [cost, estimation, prediction, pricing, calculator]
---

## Description

Estimate the cost of an extraction before running it, based on page
count, document density, output length, and chosen skill/template.

## Motivation

From `agentic agent builder.md`: agentic parsing costs scale
unpredictably. A pre-run cost estimate helps users decide whether to
proceed, and enables complexity-aware pricing.

## Formula

Based on the document's proposed model:
```
Cost = (0.5 × Pages) + (0.25 × OutputCharacters / 1000)
```

In ADE context:
```
EstimatedCost = BasePerPage × Pages
              + TokenRate × EstimatedTokens
              + ToolCost × ExpectedToolCalls
```

Where:
- `BasePerPage` = document pre-processing cost
- `TokenRate` = LLM/VLM cost per 1K tokens
- `EstimatedTokens` = prompt tokens (from skill size) × expected cycles
- `ExpectedToolCalls` = based on template field count and skill probe order
- `ToolCost` = OCR/VLM per-call cost from provider registry

## API

```
POST /api/v1/runs/estimate
{
  "definition_id": "...",
  "document_id": "..."
}

Response:
{
  "estimated_cost_usd": 0.42,
  "estimated_tokens": 4200,
  "estimated_cycles": 8,
  "estimated_tool_calls": 12,
  "breakdown": {...}
}
```

## UI

- Before starting a run, show estimated cost in Pane 1
- "This extraction is estimated to cost $0.42 and use 4,200 tokens"
- Warn if estimate exceeds 50% of run budget

## Acceptance Criteria

- [ ] `POST /api/v1/runs/estimate` endpoint
- [ ] Cost estimation based on document metadata
- [ ] Token estimation based on skill/template
- [ ] Tool call estimation based on probe order
- [ ] UI displays estimate before run
- [ ] Warning if estimate > 50% of budget
- [ ] Test: estimate within ±30% of actual cost

## Constraints

- Estimate is heuristic, not a guarantee
- Accuracy improves with actual run data (learn from past runs)
- v1: simple model; v2: ML-based prediction

## Dependencies

- BLK-050 (token/cost tracking)
- BLK-059 (document pre-processing metadata)
