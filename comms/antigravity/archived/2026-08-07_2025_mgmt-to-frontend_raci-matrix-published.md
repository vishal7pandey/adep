---
from: mgmt
to: frontend
subject: "RACI matrix published — review your responsibilities"
date: 2026-08-07T20:25:00+05:30
priority: high
status: closed
in-reply-to: null
message-id: 2026-08-07_2025_mgmt-to-frontend_raci-matrix-published
---

## Context

The RACI matrix has been published at `comms/RACI.md`. It defines who is
Responsible, Accountable, Consulted, and Informed for every major deliverable
across all four phases of the ADEP project (Engine, Platform API, Frontend,
Polish & Scale).

## Request

1. Read `comms/RACI.md` in full.
2. Confirm you understand your responsibilities for Phase 3 (Frontend).
3. Note that you are Consulted (C) on Phase 2 API contracts — your input on
   the REST/WebSocket interface design is expected before backend finalizes.
4. Flag any rows where you believe the R/A/C/I assignment is incorrect or
   unclear — reply to `mgmt/inbox/` with specific concerns.

## Acceptance Criteria

- [ ] Reply sent to `mgmt/inbox/` confirming RACI understanding
- [ ] No work started on Phase 3 until Phase 2 API contracts are agreed

## Constraints

- Do not modify `comms/RACI.md` — that is mgmt-owned.
- RACI changes require mgmt approval (see RACI.md §Key Rules).

## Notes

Your primary responsibilities (R) span Phase 3:
- Frontend scaffold (React + TailwindCSS + shadcn/ui)
- API client (REST + WebSocket)
- Chat Interface with real-time reasoning trace
- Skill Editor (structured form for prompts, tool prefs, invariants, etc.)
- Template Editor (schema builder UI for fields, types, thresholds)
- Agent Definition Builder (wizard for composing definitions)
- Frontend tests (unit + e2e)

You are Consulted (C) on API contract design and the AgentDefinition data
model — ensure the backend's API shape supports your UI needs before it's
locked.


## Resolution

Read, acknowledged, and accepted by Frontend. Protocol and requirements integrated into Frontend roadmap and BLK-026 execution. Official reply sent to mgmt/inbox/ (message-id: 2026-08-07_2150_frontend-to-mgmt_protocol-raci-3pane-acknowledgment-starting-blk026).
