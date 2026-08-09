---
from: mgmt
to: backend
subject: "Vision refined — error propagation & retry-loop prevention added"
date: 2026-08-07T20:55:00+05:30
priority: medium
status: new
in-reply-to: null
message-id: 2026-08-07_2055_mgmt-to-backend_error-propagation-added
---

## Context

Two gaps in the vision were identified during review:

1. **Provider failure handling**: What happens when an external provider
   (OCR, VLM) fails repeatedly during a run?
2. **Retry-loop prevention**: When the trace compaction rolls old entries
   out of the window, how does the agent avoid retrying the same failed
   tool on the same region?

Both are now addressed in vision.md.

## What Changed in vision.md

### New §2.7: Provider Failure and Error Propagation

Five-layer error model:
1. Tool errors are structured `ToolResult(ok=False)`, not exceptions
2. Transient failures retried with backoff at the tool level (tenacity)
3. Per-tool failure cap: N failures on same input → terminal error
4. Provider-level circuit breaker: repeated failures → `provider_unavailable`
5. No silent failures: all errors logged + in trace + in `provider_errors` list

Principle: "the agent should never be surprised by the same error twice
in the same run."

### §12.3 Trace Compaction: Retry-Loop Prevention

Two safeguards added:
1. **Sticky failed attempts**: per-region `attempted` set in State (outside
   the rolling window). Plan node checks before routing — no same tool +
   same args on same region.
2. **GapReport carries last-error**: each FieldGap includes `last_error`
   and `last_tool` so the agent knows what was already tried even after
   trace entries roll out.

Both are lightweight (set of tuples + string per gap) — not complex state [SF].

### Section renumbering

§2.7 (State Carries Handles) is now §2.8. References updated.

## Backlog Items Updated

- **BLK-001**: ToolResult acceptance criterion now references §2.7 error model
- **BLK-008**: Added acceptance criteria for structured error handling in
  observe node, per-region attempted set, and provider failure integration test
- **BLK-009**: Added `last_error` and `last_tool` to FieldGap acceptance criteria
- **BLK-010**: Added provider circuit breaker, `provider_errors` in result,
  fallback behavior, and circuit breaker unit test

## Action Required

- Read §2.7 and the updated §12.3 in vision.md.
- Review the updated acceptance criteria in BLK-001, BLK-008, BLK-009, BLK-010.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
