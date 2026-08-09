---
from: mgmt
to: backend
subject: "PM system live — backlog, process, and your pending assignments"
date: 2026-08-07T20:35:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-07_2035_mgmt-to-backend_pm-system-live
---

## Context

The project management system is now live. Three new top-level directories
have been created:

- `backlog/` — all pending work items, categorized by features/, bugs/,
  ideas/, tech-debt/, plus an in-progress/ subdirectory for active items.
- `implemented/` — completed items, same category structure.
- `projectmgmt/` — process documentation, item template, and live status
  board.

The full process is documented in `projectmgmt/PROCESS.md`. Read it.

## Request

1. Read `projectmgmt/PROCESS.md` in full — understand the item lifecycle,
   communication cadence, and your responsibilities.
2. Read `projectmgmt/STATUS.md` — this is the live dashboard. Check it at
   the start of every work session.
3. Review your Phase 1 backlog items: BLK-001 through BLK-015. These are
   all in `backlog/features/`.
4. Acknowledge by replying to `mgmt/inbox/` confirming you've read the
   process and are ready for assignment.

## The Overcommunication Rule

**Everyone overcommunicates.** Per PROCESS.md §5:

- Starting work on an item → comms to mgmt/inbox/
- Blocked on an item → comms to mgmt/inbox/ (+ blocker's inbox if another party)
- Completed an item → comms to mgmt/inbox/ with summary
- End of work session → comms to mgmt/inbox/ with progress summary

Every backlog lifecycle event triggers a comms message. Reference the
BLK-NNN ID in your comms messages so we can cross-reference.

## Acceptance Criteria

- [ ] Reply sent to `mgmt/inbox/` confirming PROCESS.md read and understood
- [ ] Confirm understanding of the overcommunication rule
- [ ] No work started until items are formally assigned by mgmt

## Constraints

- Do not modify `projectmgmt/`, `backlog/`, or `implemented/` — these are
  mgmt-owned. You may create backlog items (proposals) but mgmt assigns
  and moves them.
- Do not modify `comms/` — that is mgmt-owned.

## Notes

Your Phase 1 items (BLK-001 to BLK-015) cover: tool contracts, package
scaffolding, tool registry, four providers (PaddleOCR, Tesseract, Azure
GPT-5.4 VLM, PIL+OpenCV), ReAct graph, outcome validator, give-up caps,
InvoiceSkill, InvoiceTemplate, run() entry point, unit tests, and
evaluation harness.

Dependencies are declared in each item's frontmatter. BLK-001 (tool
interface contracts) is the foundation — everything depends on it.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
