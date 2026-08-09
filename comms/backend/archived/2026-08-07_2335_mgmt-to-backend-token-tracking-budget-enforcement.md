---
from: mgmt
to: backend
subject: "NEW: Token tracking + budget enforcement — BLK-050, BLK-051 (high priority)"
date: 2026-08-07T23:35:00+05:30
priority: high
status: new
in-reply-to: 2026-08-07_2325_mgmt-to-backend_wave3-skills-trajectory-hitl-eval
message-id: 2026-08-07_2335_mgmt-to-backend-token-tracking-budget-enforcement
---

## Why This Matters

Every ReAct cycle makes an LLM call. Without token tracking, we're
flying blind on cost. A single runaway extraction (stuck in retries,
200-page document) could burn through an entire API quota silently.

vision.md §15 (Token & Cost Management) has been added. Two new high-
priority backlog items are now in your queue.

## New Tasks

### BLK-050 — Token tracking & cost calculation (HIGH)

**What:** Track token consumption for every LLM call in the ReAct loop.

**Key deliverables:**
- `TokenUsage` dataclass: `node`, `cycle`, `input_tokens`, `output_tokens`, `total_tokens`, `cost_usd`, `timestamp`
- `token_usage: list[TokenUsage]` in AgentState + `total_tokens` + `total_cost_usd` running totals
- LLM pricing config in `config.py` (input/output per 1K, separate LLM vs VLM rates)
- Capture token counts from Azure API response (`usage.prompt_tokens`, `usage.completion_tokens`)
- `tiktoken` fallback if provider doesn't return counts
- Record in `plan_node`, `compact_node`, and semantic check (if LLM-assisted)
- SSE `token_usage` event after each LLM call:
  ```json
  {"type": "token_usage", "node": "plan", "cycle": 5, "input_tokens": 1200, "output_tokens": 150, "total_tokens": 1350, "cost_usd": 0.008, "running_total_tokens": 8500, "running_total_cost": 0.052}
  ```
- `ExtractedResult` includes token usage summary
- Persist to `.adep/runs/{run_id}/token_usage.json`
- Aggregate to `.adep/stats/aggregate.json` (total tokens, cost, runs, avg, by day)
- New admin API endpoints:
  - `GET /api/v1/admin/stats` — today's aggregates
  - `GET /api/v1/admin/consumption` — 7-day daily breakdown
  - `GET /api/v1/admin/runs` — recent runs (paginated, sortable)
  - `GET /api/v1/admin/runs/expensive` — top expensive runs (30 days)
  - `GET /api/v1/admin/settings` — current budget + pricing config
  - `PUT /api/v1/admin/settings` — update config

**See BLK-050 for full spec.**

### BLK-051 — Budget limits & enforcement (HIGH)

**What:** Enforce token/cost budgets at 3 levels. Graceful termination
when exceeded — never silent failures.

**Budget levels:**
| Level | Warning (80%) | Limit (100%) |
|-------|---------------|--------------|
| Run | SSE `budget_warning`, Pane 1 banner | Agent terminates PARTIAL |
| Definition (daily) | Admin alert | New runs blocked (429) |
| Global (daily) | Admin alert | All new runs blocked (429) |

**Config additions:**
```python
budget_per_run_tokens: int = 100_000
budget_per_run_cost_usd: float = 1.0
budget_per_definition_daily_tokens: int = 1_000_000
budget_per_definition_daily_cost_usd: float = 10.0
budget_global_daily_tokens: int = 10_000_000
budget_global_daily_cost_usd: float = 100.0
budget_warning_threshold: float = 0.8
```

**Enforcement points:**
1. `POST /runs`: pre-check definition + global daily budgets (429 if exceeded)
2. After each LLM call: check run budget (terminate if exceeded)
3. On run completion: update daily aggregates

**New SSE events:**
- `budget_warning` — at 80% of any budget level
- `budget_exceeded` — at 100% of any budget level

**New endpoint:**
- `GET /api/v1/budget` — current consumption at all levels

**See BLK-051 for full spec.**

## Updated Pipeline

| Wave | Items | Status |
|------|-------|--------|
| 1 | BLK-039, BLK-046, BLK-043 | ✅ Done |
| 2 | BLK-040, BLK-041, BLK-044 | Assigned (working) |
| 2.5 | **BLK-050, BLK-051** | **NEW — high priority, slot after Wave 2** |
| 3 | BLK-042, BLK-049, BLK-047, BLK-015 | Queued |

**Sequencing note:** BLK-050 should come right after Wave 2 (it's
independent of the skill library). BLK-051 depends on BLK-050. The
admin API endpoints in BLK-050 unblock the frontend admin panel (BLK-052).

## Action Required

1. Continue Wave 2 (BLK-040, BLK-041, BLK-044)
2. After Wave 2: implement BLK-050 (token tracking) then BLK-051 (budgets)
3. These are HIGH priority — they protect against cost overruns
4. Acknowledge by replying to `mgmt/inbox/`


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
