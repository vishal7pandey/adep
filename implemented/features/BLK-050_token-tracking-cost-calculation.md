---
id: BLK-050
type: feature
title: "Token tracking & cost calculation — per-run, per-node consumption"
priority: high
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T23:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-008, BLK-039]
tags: [backend, tokens, cost, monitoring, observability, budgeting]
---

## Description

Track token consumption for every LLM call in the ReAct loop. Each call
to the LLM (plan node, compact node, semantic checks) records input
tokens, output tokens, and calculated cost. Data persists per-run and
aggregates for admin dashboards.

## Motivation

The global rules [TM] require: track and log token usage for cost
monitoring, implement token counting before API calls, monitor and
alert on unusual token consumption. Without this, we're flying blind
on LLM costs — a single runaway extraction could burn through a
budget silently.

## Design

### TokenUsage Dataclass

```python
@dataclass
class TokenUsage:
    """Token consumption for a single LLM call."""
    node: str           # "plan", "compact", "semantic_check"
    cycle: int          # ReAct cycle number
    input_tokens: int
    output_tokens: int
    total_tokens: int   # input + output
    cost_usd: float     # calculated from model pricing
    timestamp: str      # ISO 8601
```

### AgentState Addition

- `token_usage: list[TokenUsage]` — per-call log, accumulates across the run
- `total_tokens: int` — running total (denormalized for quick access)
- `total_cost_usd: float` — running cost total

### Cost Calculation

Model pricing stored in config (per 1K tokens):
```python
# config.py additions
llm_pricing_input_per_1k: float = 0.005   # $/1K input tokens
llm_pricing_output_per_1k: float = 0.015  # $/1K output tokens
vlm_pricing_input_per_1k: float = 0.01    # $/1K input tokens (vision)
vlm_pricing_output_per_1k: float = 0.03   # $/1K output tokens (vision)
```

Cost = `(input_tokens / 1000) * pricing_input + (output_tokens / 1000) * pricing_output`

### Token Counting

- Azure OpenAI returns token counts in the API response
  (`usage.prompt_tokens`, `usage.completion_tokens`)
- Capture these from every `llm_client.invoke()` call
- If provider doesn't return counts, use `tiktoken` for estimation
- Log a warning if estimated vs actual differs by >10%

### Integration Points

1. **plan_node**: After `llm_client.invoke()`, record TokenUsage
2. **compact_node**: After LLM summarization call, record TokenUsage
3. **semantic_check** (in validator): If LLM-assisted, record TokenUsage
4. **SSE `token_usage` event**: Emit after each LLM call
   ```json
   {"type": "token_usage", "node": "plan", "cycle": 5, "input_tokens": 1200, "output_tokens": 150, "total_tokens": 1350, "cost_usd": 0.008, "running_total_tokens": 8500, "running_total_cost": 0.052}
   ```
5. **ExtractedResult**: Include `token_usage` summary in final result
   ```json
   {"total_tokens": 8500, "total_cost_usd": 0.052, "by_node": {"plan": {"calls": 8, "tokens": 7000}, "compact": {"calls": 1, "tokens": 1500}}}
   ```

### Persistence

- Token usage saved to `.adep/runs/{run_id}/token_usage.json`
- Aggregated stats saved to `.adep/stats/aggregate.json` (updated on run completion)
- Aggregate tracks: total tokens, total cost, runs count, avg tokens/run, avg cost/run, by day

## Acceptance Criteria

- [ ] `TokenUsage` dataclass in `state.py`
- [ ] `token_usage: list[TokenUsage]` added to AgentState
- [ ] `total_tokens: int` and `total_cost_usd: float` in AgentState
- [ ] LLM pricing config in `config.py` (input/output per 1K, separate for LLM vs VLM)
- [ ] `plan_node` captures and records token usage after each LLM call
- [ ] `compact_node` captures and records token usage
- [ ] Semantic check (if LLM-assisted) captures and records token usage
- [ ] SSE `token_usage` event emitted after each LLM call
- [ ] `ExtractedResult` includes token usage summary
- [ ] Per-run `token_usage.json` persisted to `.adep/runs/{run_id}/`
- [ ] Aggregate stats persisted to `.adep/stats/aggregate.json`
- [ ] `tiktoken` fallback for token estimation when provider doesn't return counts
- [ ] Warning logged when estimate vs actual differs >10%
- [ ] Unit test: token usage accumulates correctly across multiple cycles
- [ ] Unit test: cost calculation matches expected formula
- [ ] Unit test: compaction token usage recorded separately
- [ ] Integration test: full run produces correct token_usage.json

## Constraints

- Token tracking must not add latency — capture from API response, don't make extra calls [SF]
- Cost is an estimate based on configured pricing, not a billing system [SF]
- v1: single-tenant, no per-user tracking. Multi-tenant tracking is BLK-037 (v2).
- `tiktoken` is optional — only used if provider doesn't return counts

## Dependencies

- BLK-008 (ReAct graph — plan/compact nodes where LLM calls happen)
- BLK-039 (Compaction — compact node makes LLM calls)

## Notes

- Global rules [TM]: Track and log token usage for cost monitoring
- vision.md §15 (new) — Token & Cost Management
- Prefixes the admin panel (BLK-052) and budget enforcement (BLK-051)
