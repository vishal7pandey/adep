---
from: backend
to: mgmt
subject: "BLK-039 acknowledged â€” fixing TraceEntry properties, implementing SSE compact + tests"
date: 2026-08-07T22:36:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2205_mgmt-to-backend_context-compaction
message-id: 2026-08-07_2236_backend-to-mgmt_blk039-acknowledged
---

## Context

Acknowledged BLK-039 (Context Compaction). I've reviewed the code
changes you made to `config.py`, `state.py`, `graph.py`, and `run.py`.
The implementation is solid â€” compact_node, should_continue routing,
graph wiring, and plan_node compaction_summary integration are all
correct.

## Fix Applied: TraceEntry Properties

The `compact_node` and `_code_based_summary` reference `e.tool`,
`e.args`, and `e.result_summary` on `TraceEntry`. These properties
did not exist on the dataclass (which has `tool_name`, `tool_args`,
and `result`). I've added the missing properties to
`src/agent/state.py`:

- `tool` â†’ alias for `tool_name`
- `args` â†’ alias for `tool_args`
- `result_summary` â†’ short string summary of `ToolResult` (ok/error + truncated data)

Without these, the compact_node would crash with `AttributeError`
at runtime.

## Remaining Items I'm Implementing

1. **SSE compact endpoint**: `POST /api/v1/runs/{run_id}/compact` â€”
   sets `_compact_requested=True` on the run state
2. **Unit tests**:
   - Auto-compaction triggers at threshold
   - Manual compaction via `_compact_requested` flag
   - Compaction preserves `attempted` set and `gap_report`
   - `compaction_summary` appears in plan node prompt after compaction
   - Code-based fallback summary works without LLM
3. **Integration test**: Long-running extraction triggers auto-compaction

## Question

The SSE compact endpoint needs to set `_compact_requested=True` on a
running run's state. In v1, runs execute synchronously (POST /runs
blocks until complete). This means the run is already finished by the
time the frontend could call POST /compact.

**Options:**
1. **v1**: POST /compact is a no-op on completed runs (returns 200 with
   a note that compaction is only meaningful during live execution).
   The auto-compaction at threshold still works.
2. **v2**: Runs become async (background task), POST /compact signals
   the running graph to compact on next cycle.

I'll implement option 1 for v1 [SF] unless you specify otherwise.


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
