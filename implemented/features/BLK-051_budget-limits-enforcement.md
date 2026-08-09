---
id: BLK-051
type: feature
title: "Budget limits & enforcement — per-run and per-definition token caps"
priority: high
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T23:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-050]
tags: [backend, tokens, budget, limits, enforcement, safety, cost]
---

## Description

Enforce token/cost budgets at three levels: per-run, per-definition, and
global. When a budget is approached, the agent emits warnings. When
exceeded, the agent terminates gracefully with partial results.

## Motivation

Without budget enforcement, a runaway extraction (stuck in a retry loop,
processing a 200-page document) could burn through an entire API quota
silently. Budgets are the financial equivalent of the give-up caps
(§2.6) that already exist for cycle counts.

## Design

### Budget Configuration

```python
# config.py additions
budget_per_run_tokens: int = 100_000        # max tokens per single run
budget_per_run_cost_usd: float = 1.0        # max cost per single run ($)
budget_per_definition_daily_tokens: int = 1_000_000  # per definition per day
budget_per_definition_daily_cost_usd: float = 10.0   # per definition per day ($)
budget_global_daily_tokens: int = 10_000_000  # global daily cap
budget_global_daily_cost_usd: float = 100.0   # global daily cap ($)
budget_warning_threshold: float = 0.8        # warn at 80% of budget
```

### Budget Levels

| Level | Scope | What Happens at Warning (80%) | What Happens at Limit (100%) |
|-------|-------|-------------------------------|------------------------------|
| Run | Single extraction run | SSE `budget_warning` event, Pane 1 banner | Agent terminates with PARTIAL status, `budget_exceeded` reason |
| Definition | Per definition, per day | SSE `budget_warning`, admin dashboard alert | New runs for this definition blocked, `POST /runs` returns 429 |
| Global | All runs, per day | SSE `budget_warning`, admin dashboard alert | All new runs blocked, `POST /runs` returns 429 |

### Enforcement Points

1. **Before run starts** (`POST /runs`):
   - Check definition daily budget — if exceeded, return 429
   - Check global daily budget — if exceeded, return 429
   - Return remaining budget in response

2. **After each LLM call** (in plan_node, compact_node):
   - Check per-run budget — if exceeded, set status to PARTIAL with
     `budget_exceeded` reason, route to terminate
   - If at 80% threshold, emit SSE `budget_warning`

3. **On run completion**:
   - Update definition daily aggregate in `.adep/stats/`
   - Update global daily aggregate

### SSE Events

```json
// Budget warning (80% threshold)
{
  "type": "budget_warning",
  "level": "run",
  "consumed_tokens": 82000,
  "budget_tokens": 100000,
  "consumed_cost_usd": 0.82,
  "budget_cost_usd": 1.0,
  "percentage": 82,
  "message": "Approaching run budget limit — 82% consumed"
}

// Budget exceeded (100%)
{
  "type": "budget_exceeded",
  "level": "run",
  "consumed_tokens": 100500,
  "budget_tokens": 100000,
  "consumed_cost_usd": 1.005,
  "budget_cost_usd": 1.0,
  "message": "Run budget exceeded — terminating with partial results"
}
```

### API Response — Budget Info

`POST /api/v1/runs` response includes budget status:
```json
{
  "id": "...",
  "status": "running",
  "budget": {
    "run_remaining_tokens": 100000,
    "run_remaining_cost_usd": 1.0,
    "definition_daily_remaining_tokens": 950000,
    "definition_daily_remaining_cost_usd": 9.5,
    "global_daily_remaining_tokens": 9800000,
    "global_daily_remaining_cost_usd": 98.0
  }
}
```

### New Endpoint — Budget Status

```
GET /api/v1/budget
```
Returns current budget consumption for all levels:
```json
{
  "run": {"tokens": 0, "cost_usd": 0.0, "limit_tokens": 100000, "limit_cost_usd": 1.0},
  "definition_daily": {"tokens": 50000, "cost_usd": 0.5, "limit_tokens": 1000000, "limit_cost_usd": 10.0},
  "global_daily": {"tokens": 200000, "cost_usd": 2.0, "limit_tokens": 10000000, "limit_cost_usd": 100.0},
  "warnings": []
}
```

## Acceptance Criteria

- [ ] Budget config in `config.py` (6 settings + warning threshold)
- [ ] Pre-run check in `POST /runs`: block if definition/global daily budget exceeded (429)
- [ ] Per-run check after each LLM call: terminate if run budget exceeded
- [ ] 80% warning threshold triggers SSE `budget_warning` event
- [ ] 100% triggers SSE `budget_exceeded` event + graceful termination
- [ ] `GET /api/v1/budget` endpoint returns current consumption at all levels
- [ ] `POST /runs` response includes remaining budget info
- [ ] Daily aggregates persisted in `.adep/stats/` (reset on date change)
- [ ] Budget exceeded termination produces PARTIAL result with `budget_exceeded` reason
- [ ] Unit test: run budget exceeded → agent terminates with partial result
- [ ] Unit test: 80% threshold → warning event emitted
- [ ] Unit test: definition daily budget exceeded → new run blocked with 429
- [ ] Unit test: daily aggregate resets on date change
- [ ] Integration test: runaway extraction hits run budget and terminates

## Constraints

- Budget enforcement is non-blocking for agent logic — checks happen after LLM calls, not before every tool [SF]
- Graceful termination: partial results are preserved, not discarded
- v1: budgets are global config, not per-user. Per-user budgets require BLK-037 (multi-tenant).
- Daily reset is date-based (midnight UTC), not rolling 24h window [SF]

## Dependencies

- BLK-050 (Token tracking — provides the consumption data)

## Notes

- Global rules [TM]: Monitor and alert on unusual token consumption
- Complements give-up caps (§2.6) — cycle caps prevent loops, budget caps prevent cost overruns
- Admin panel (BLK-052) surfaces this data to humans
