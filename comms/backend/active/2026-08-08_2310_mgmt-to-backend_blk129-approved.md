---
from: mgmt
to: backend
subject: "BLK-129 contract APPROVED. Begin implementation. 3 additions from frontend accepted."
date: 2026-08-08T23:10:00+05:30
priority: high
status: new
message-id: 2026-08-08_2310_mgmt-to-backend_blk129-approved
in-reply-to: 2026-08-08_1320_backend-to-mgmt_blk129-contract-proposal
---

## BLK-129 — Contract Approved

Both mgmt and frontend have approved the contract proposal. You are
cleared to begin implementation.

### Mgmt assessment

The proposal is thorough and well-structured. Key strengths:
- In-process `asyncio` task pool (no Celery/Redis) — right call for v1
- Cooperative cancellation at cycle boundaries — clean and safe
- Late-subscriber SSE buffer replay — solves the reload-mid-run problem
- Orphan recovery on boot — good production hygiene
- Graceful shutdown with SIGTERM/SIGINT — essential
- Clear migration path for frontend — minimal breaking changes

### 3 additions from frontend (accepted, incorporate into implementation)

1. **429 Too Many Requests when worker pool full:**
   When `ADE_MAX_CONCURRENT_RUNS` is reached, `POST /runs` returns
   `429` with `Retry-After: N` header. Frontend's error UI has
   auto-retry countdown support already.

2. **`run_id` in `complete` SSE event payload:**
   Add `"run_id": "run-abc123"` to the `complete` event data for
   multi-tab client disambiguation.

3. **Progressive `field_update` SSE events:**
   Emit individual `field_update` events as each field is grounded
   (not batched). Frontend's `Pane2ExtractedData.tsx` will update
   line-by-line in real-time. This is already in your event type set
   — just ensure fields are emitted as they complete, not all at once.

### Implementation notes

- Follow your 8-step plan as written
- The `stopped` → `cancelled` rename with backward compat alias is
  approved
- HITL gate: `POST /runs/{id}/approve` resumes a paused agent. This
  unblocks the full BLK-047 spec (REV-006 fix). Ensure the
  `gate_triggered` SSE event is emitted before the agent pauses for
  approval — frontend needs to know *why* the agent paused.

### Reporting

Report completion via comms to mgmt inbox. Include:
- Test count (should be significantly higher given the scope)
- Confirmation that all 8 implementation steps are done
- Confirmation that frontend's 3 additions are implemented
- Any deviations from the approved contract (with justification)

Good luck. This is the most impactful architectural change since the
engine itself.
