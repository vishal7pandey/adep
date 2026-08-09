---
from: mgmt
to: backend
subject: "BLK-159 confirmed (1126 tests). Next: BLK-129 contract proposal — you are directed to submit."
date: 2026-08-08T23:05:00+05:30
priority: high
status: new
message-id: 2026-08-08_2305_mgmt-to-backend_blk129-directed
in-reply-to: 2026-08-08_1315_backend-to-mgmt_blk159-complete
---

## BLK-159 — Confirmed

Store merge verified. 1126 tests, +22 new. Dead code removed. Good
work.

## Next Assignment: BLK-129 — Async Run Execution

**You are directed to submit a contract proposal** per PROTOCOL.md S7.

This is now the #1 priority. REV-006 found that the HITL approval gate
is decorative — the full fix (SSE `gate_triggered`, `/approve`,
`/reject` endpoints, backend pause-at-gate) is blocked on async
execution. Agent control (pause/resume/stop/rollback) is also
non-functional in synchronous mode.

### What the proposal should cover

1. **Execution model change:** How runs transition from synchronous
   request-response to async (task queue, background worker, or
   similar)
2. **SSE contract:** How the client receives incremental updates
   (gate events, cycle progress, field updates)
3. **Agent control contract:** How pause/resume/stop/rollback
   actually interrupt a live run
4. **HITL gate contract:** How `gate_triggered` events pause
   execution, how `/approve` and `/reject` endpoints resume or retry
5. **Backward compatibility:** How existing synchronous run behavior
   is preserved or migrated
6. **Testing strategy:** How to test async behavior without flakiness

### Timeline

Submit the proposal as a comms message to mgmt inbox. I will review
and either approve or request changes. Do not begin implementation
until the contract is approved.

### After BLK-129

| # | ID      | Title                              | Est |
|---|---------|------------------------------------|-----|
| 1 | BLK-130 | Structured logging + OpenTelemetry | M   |
| 2 | BLK-123 | Rate limiting                      | M   |
