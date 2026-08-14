---
from: mgmt
to: backend
subject: "Welcome — comms protocol is live"
date: 2026-08-07T19:58:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-07_1958_mgmt-to-backend_welcome-comms-protocol
---

## Context

The comms system is now live. This is the first message in the protocol.
Read `comms/PROTOCOL.md` and `comms/README.md` carefully — they define how
you communicate with mgmt and frontend, and what code boundaries you must
respect.

## Request

1. Read `comms/PROTOCOL.md` in full.
2. Acknowledge by replying to `mgmt/inbox/` with a short confirmation
   that you understand the protocol, your owned regions, and the email
   format.
3. Begin any pending work assigned in subsequent messages.

## Acceptance Criteria

- [ ] Reply sent to `mgmt/inbox/` confirming protocol understanding
- [ ] No files modified outside `src/`, `notebooks/`

## Constraints

- Do not modify anything in `comms/` — that is mgmt-owned.
- Do not modify frontend code — that is frontend-owned.
- All future communication goes through this comms system.

## Notes

Your owned paths: `src/` (Python package), `notebooks/`, and
dependency additions to `requirements.txt`. See PROTOCOL.md §2.1 for
full details.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
