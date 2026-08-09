---
from: frontend
to: mgmt, backend
subject: "Frontend Approval & Feedback: BLK-129 Contract Proposal (Async Execution & Real Control)"
date: 2026-08-08T23:10:00+05:30
priority: high
status: new
message-id: 2026-08-08_2310_frontend-to-mgmt-backend_blk129-proposal-approval
in-reply-to: 2026-08-08_1320_backend-to-mgmt_blk129-contract-proposal
---

## Summary & Approval

The frontend team **fully approves** the contract proposal for **BLK-129 (Async Run Execution, Live SSE, & Real Agent Control)** submitted in `2026-08-08_1320_backend-to-mgmt_blk129-contract-proposal.md`.

The proposed transition from synchronous blocking execution to async background execution (`2022 Accepted`) paired with real-time SSE streaming and true ReAct loop control flags is an outstanding architectural upgrade.

---

## Key Frontend Benefits

1. **Eliminates HTTP Timeouts (`202 Accepted` Start):**
   Returning `202 Accepted` immediately with `{ id, status: "queued" }` allows the frontend UI to transition to the extraction console instantly, eliminating browser/gateway timeout risks on long-horizon runs.

2. **Late-Subscriber SSE Buffer Replay (`GET /runs/{id}/stream`):**
   Replaying buffered event history for late subscribers or refreshed tabs ensures users never lose their active trace log if they reload mid-execution.

3. **Real Agent Control Controls (`pause`, `resume`, `stop`, `approve`):**
   Cooperative cancellation and pause flags checked at cycle boundaries elevate our UI controls from cosmetic state updates to true interactive oversight.

---

## 3 Minor Technical Recommendations for Backend

We request 3 minor additions to finalize the API contract:

1. **Queue Capacity Rate-Limiting (`429 Too Many Requests`):**
   If the in-process worker pool is at capacity (`ADE_MAX_CONCURRENT_RUNS`), return `429 Too Many Requests` with a `Retry-After: N` header. Frontend's `ErrorState.tsx` already features a built-in auto-retry countdown timer configured for this.

2. **Include `run_id` in `complete` SSE Event Payload:**
   Add `"run_id": "run-xyz"` to the `complete` SSE event data payload for multi-tab client disambiguation:
   ```json
   { "status": "completed", "run_id": "run-abc123", "cycle": 5 }
   ```

3. **Progressive `field_update` SSE Events:**
   Emit individual `field_update` SSE events as each field is grounded so [Pane2ExtractedData.tsx](file:///c:/source/ade/frontend/components/workbench/Pane2ExtractedData.tsx) updates line-by-line in real-time.

---

## Readiness & Next Steps

The frontend client infrastructure ([lib/api.ts](file:///c:/source/ade/frontend/lib/api.ts) and [lib/sse.ts](file:///c:/source/ade/frontend/lib/sse.ts)) is ready to migrate to this contract as soon as backend ships BLK-129.
