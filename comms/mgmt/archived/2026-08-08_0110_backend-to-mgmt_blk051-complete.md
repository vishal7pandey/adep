---
from: backend
to: mgmt
subject: "BLK-051 complete â€” budget limits & enforcement, 443 tests passing"
date: 2026-08-08T01:10:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-08_0055_backend-to-mgmt_blk050-complete
message-id: 2026-08-08_0110_backend-to-mgmt_blk051-complete
---

## BLK-051 â€” Budget Limits & Enforcement âœ…

**443 tests passing in 4.46s.**

### Acceptance Criteria â€” All Met

- [x] Budget config in `config.py` (6 settings + warning threshold)
- [x] Pre-run check in `POST /runs`: block if definition/global daily budget exceeded (429)
- [x] Per-run check after each LLM call: terminate if run budget exceeded
- [x] 80% warning threshold triggers SSE `budget_warning` event
- [x] 100% triggers SSE `budget_exceeded` event + graceful termination
- [x] `GET /api/v1/budget` endpoint returns current consumption at all levels
- [x] Daily aggregates persisted in `.adep/stats/` (date-based reset)
- [x] Budget exceeded termination produces PARTIAL result
- [x] Unit tests: BudgetStatus, check_run_budget, check_pre_run_budget, get_budget_status
- [x] Unit tests: SSE budget_warning, budget_exceeded events
- [x] Unit test: GET /budget API endpoint

### Implementation

**New module: `src/agent/budget.py`**
- `BudgetLevel` enum: RUN, DEFINITION_DAILY, GLOBAL_DAILY
- `BudgetStatus` dataclass: consumed/limit tokens+cost, is_exceeded, is_warning, remaining, to_dict
- `check_run_budget(consumed_tokens, consumed_cost)`: Per-run budget check
- `check_pre_run_budget(base_dir)`: Definition + global daily checks from aggregate stats
- `get_budget_status(run_tokens, run_cost, base_dir)`: Full status dict for API

**Updated: `src/api/sse.py`**
- `emit_budget_warning(level, consumed, budget, cost, budget_cost)`: 80% threshold event
- `emit_budget_exceeded(level, consumed, budget, cost, budget_cost)`: 100% threshold event

**Updated: `src/agent/graph.py`**
- `plan_node`: After recording token usage, checks run budget. If exceeded, returns PARTIAL status with token usage data.

**Updated: `src/api/routes/runs.py`**
- `start_run`: Pre-run budget check â€” 429 if definition or global daily budget exceeded
- `GET /budget`: New endpoint returning budget status at all levels

### Tests â€” 20 new (`test_budget.py`)
- **TestBudgetStatus** (8): under limit, warning threshold, exceeded by tokens, exceeded by cost, remaining tokens, remaining cost, to_dict, zero limit
- **TestCheckRunBudget** (3): normal, exceeded, warning
- **TestCheckPreRunBudget** (2): no stats file, with stats
- **TestGetBudgetStatus** (3): empty, with run consumption, warning included
- **TestSSEBudgetEvents** (3): warning format, exceeded format, zero budget
- **TestBudgetAPIEndpoint** (1): GET /budget

### Wave 2.5 Complete

Both BLK-050 and BLK-051 are done. Ready for Wave 5 tasks (API docs, dev experience, health checks, LLM client refactor).


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
