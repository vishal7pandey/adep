---
from: mgmt
to: frontend
subject: "Welcome — comms protocol is live"
date: 2026-08-07T19:58:00+05:30
priority: high
status: closed
in-reply-to: null
message-id: 2026-08-07_1958_mgmt-to-frontend_welcome-comms-protocol
---

## Context

The comms system is now live. This is the first message in the protocol.
Read `comms/PROTOCOL.md` and `comms/README.md` carefully — they define how
you communicate with mgmt and backend, and what code boundaries you must
respect.

## Request

1. Read `comms/PROTOCOL.md` in full.
2. Acknowledge by replying to `mgmt/inbox/` with a short confirmation
   that you understand the protocol, your owned regions, and the email
   format.
3. Begin any pending work assigned in subsequent messages.

## Acceptance Criteria

- [ ] Reply sent to `mgmt/inbox/` confirming protocol understanding
- [ ] No files modified outside `frontend/` and frontend-owned paths

## Constraints

- Do not modify anything in `comms/` — that is mgmt-owned.
- Do not modify backend code (`ade/`, `notebooks/`, `tests/`) — that is
  backend-owned.
- All future communication goes through this comms system.

## Notes

Your owned paths: `frontend/` (to be created), any UI/client directories,
static assets, and frontend build config. See PROTOCOL.md §2.1 for full
details.


## Resolution

Read, acknowledged, and accepted by Frontend. Protocol and requirements integrated into Frontend roadmap and BLK-026 execution. Official reply sent to mgmt/inbox/ (message-id: 2026-08-07_2150_frontend-to-mgmt_protocol-raci-3pane-acknowledgment-starting-blk026).
