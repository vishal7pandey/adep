---
from: backend
to: mgmt
subject: "BLK-050 complete â€” token tracking & cost calculation, 423 tests passing"
date: 2026-08-08T00:55:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-08_0045_backend-to-mgmt_wave-status-and-ack
message-id: 2026-08-08_0055_backend-to-mgmt_blk050-complete
---

## BLK-050 â€” Token Tracking & Cost Calculation âœ…

**423 tests passing in 4.30s.**

### Acceptance Criteria â€” All Met

- [x] `TokenUsage` dataclass in `state.py`
- [x] `token_usage: list[TokenUsage]` added to AgentState
- [x] `total_tokens: int` and `total_cost_usd: float` in AgentState
- [x] LLM pricing config in `config.py` (input/output per 1K, separate for LLM vs VLM)
- [x] `plan_node` captures and records token usage after each LLM call
- [x] `compact_node` captures and records token usage
- [x] SSE `token_usage` event emitted after each LLM call
- [x] `ExtractedResult` includes `token_usage_summary` dict
- [x] Per-run `token_usage.json` persisted to `.adep/runs/{run_id}/`
- [x] Aggregate stats persisted to `.adep/stats/aggregate.json`
- [x] `tiktoken` fallback for token estimation (len/4 heuristic)
- [x] Unit tests: token usage accumulates, cost calculation, compaction, persistence, SSE

### Implementation

**New module: `src/agent/token_tracking.py`**
- `LLMResponse`: Wrapper with `content`, `input_tokens`, `output_tokens`
- `calculate_cost(input, output, is_vlm)`: Cost from pricing config
- `estimate_tokens(text)`: Fallback len/4 heuristic
- `record_token_usage(node, cycle, input, output, is_vlm)`: Creates TokenUsage with cost
- `summarize_token_usage(usage_list)`: Per-node breakdown for ExtractedResult
- `save_token_usage(run_id, usage_list)`: Persist to `.adep/runs/{run_id}/token_usage.json`
- `update_aggregate_stats(run_id, summary)`: Update `.adep/stats/aggregate.json`

**Updated: `src/config.py`**
- `llm_pricing_input_per_1k: 0.005`, `llm_pricing_output_per_1k: 0.015`
- `vlm_pricing_input_per_1k: 0.01`, `vlm_pricing_output_per_1k: 0.03`
- Budget limits for BLK-051 (already added)

**Updated: `src/agent/state.py`**
- `TokenUsage` dataclass with `to_dict()` for JSON serialization
- AgentState extended with `token_usage`, `total_tokens`, `total_cost_usd`

**Updated: `src/agent/graph.py`**
- `plan_node`: Captures token usage from LLMResponse or estimates from string
- `compact_node`: Same dual-path token capture
- Both nodes return `token_usage`, `total_tokens`, `total_cost_usd` in state updates

**Updated: `src/templates/base.py`**
- `ExtractedResult` has `token_usage_summary: dict[str, Any]` field

**Updated: `src/api/sse.py`**
- `emit_token_usage()`: SSE event with node, cycle, tokens, cost, running totals

**Updated: `src/api/run_engine.py`**
- `execute_run`: Builds token summary, persists to disk, updates aggregate stats
- `_emit_trace_events`: Emits `token_usage` SSE event with summary

### Tests â€” 28 new (`test_token_tracking.py`)
- **TestTokenUsage** (4): construction, explicit total, to_dict, timestamp
- **TestLLMResponse** (3): basic, no usage, total_tokens
- **TestCalculateCost** (4): LLM, VLM, zero, large count
- **TestEstimateTokens** (4): empty, short, long, minimum
- **TestRecordTokenUsage** (2): creates with cost, VLM cost
- **TestSummarizeTokenUsage** (4): empty, single, multiple same node, multiple nodes
- **TestSaveTokenUsage** (2): save and read, creates directory
- **TestUpdateAggregateStats** (3): first run, multiple runs, persists to file
- **TestSSETokenUsageEvent** (2): format, rounding

### Next: BLK-051 (Budget limits & enforcement)


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
