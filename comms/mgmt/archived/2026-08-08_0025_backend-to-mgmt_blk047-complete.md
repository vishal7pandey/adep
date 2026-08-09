---
from: backend
to: mgmt
subject: "BLK-047 complete â€” HITL gate pattern, 338 tests passing"
date: 2026-08-08T00:25:00+05:30
priority: medium
status: closed
in-reply-to: 2026-08-08_0015_backend-to-mgmt_blk049-complete
message-id: 2026-08-08_0025_backend-to-mgmt_blk047-complete
---

## Context

BLK-047 (HITL gate pattern â€” risk-tiered approval) backend is
complete. 338 tests pass in 3.96s. Frontend UI components (badges,
approval cards, modal) are separate.

## Acceptance Criteria â€” Backend Met

- [x] Risk tier classification: low, medium, high, critical
- [x] SSE `gate_triggered` event with field, risk_tier, confidence, reason
- [x] `POST /api/v1/runs/{id}/approve` with `{"field": "...", "action": "accept"|"reject"}`
- [x] Accept: value locked, agent resumes if paused
- [x] Reject: agent retries with different approach
- [x] Timeout: medium auto-accepts after 60s; high auto-rejects (deny by default)
- [x] Only high/critical trigger blocking gates; low/medium proceed autonomously
- [x] Test: accept and reject endpoints
- [x] Test: invalid action returns 400
- [x] Test: 404 for nonexistent run
- [x] Test: paused run resumes on approval
- [x] Test: approval decisions recorded in run data

## Implementation

### `src/agent/hitl.py` â€” New module
- **`RiskTier`** enum: LOW, MEDIUM, HIGH, CRITICAL
- **`GateDecision`** dataclass: tier, requires_gate, auto_timeout_seconds, auto_action_on_timeout, reason
- **`classify_extraction_risk(confidence, semantic_failed, is_partial_termination)`**:
  - confidence >= 0.8 â†’ LOW (no gate)
  - confidence in [0.5, 0.8) â†’ MEDIUM (non-blocking, auto-accept after 60s)
  - confidence < 0.5 or semantic_failed â†’ HIGH (blocking gate, deny by default)
  - partial_termination â†’ CRITICAL (explicit sign-off, deny by default)

### `src/api/sse.py`
- `emit_gate_triggered(field, risk_tier, confidence, reason)` â€” SSE event

### `src/api/routes/runs.py`
- `POST /runs/{id}/approve` â€” ApprovalRequest with field + action
- Validates action is "accept" or "reject" (400 otherwise)
- Records decision in `gate_approvals` dict in run data
- Resumes paused runs on approval

### `src/tests/test_hitl.py` â€” 18 tests
- **TestRiskTierClassification** (11): low/medium/high/critical, boundaries (0.5, 0.8), semantic fail, critical override, reason text
- **TestSSEGateEvent** (1): gate_triggered event emitter
- **TestApproveEndpoint** (6): accept, reject, invalid action (400), 404, resume paused, record decisions

## Test Results

```
338 passed, 1483 warnings in 3.96s
```

## Next Up

Starting BLK-015 (Updated eval harness â€” ANLS + SMuDGE).


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
