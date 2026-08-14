---
id: BLK-192
type: tech-debt
title: "Backlog tickets stay marked backlog/unassigned after the fix has already landed in code"
priority: medium
status: implemented
phase: 5
owner: unassigned
created: 2026-08-09T09:50:00+05:30
started: 2026-08-09T10:35:00+05:30
completed: 2026-08-09T10:35:00+05:30
estimate: S
depends-on: []
tags: [process, backlog, hygiene, trust]
---

## Description

Five tickets — BLK-167, BLK-168, BLK-169, BLK-171, BLK-172 — were filed 2026-08-08 and the corresponding fixes verifiably landed in code shortly after (same-day, per internal repo evidence), but all five were still sitting in `backlog/bugs/` with `Status: backlog` / `Owner: unassigned` as of 2026-08-09, rather than moved to `backlog/implemented/` the way BLK-156 through BLK-166 were.

This matters more than the individual stale tickets: the project has a fairly elaborate process built around this backlog (per-role `comms/` folders, ticket confirmations, phase tracking) whose whole purpose is to track ground truth about what's done. If tickets don't get closed even when the fix is verifiably in the code, the backlog stops being trustworthy — for a human skimming it, or for a future AI session that reads `BLK-169` marked `P0 / backlog / unassigned` and either re-implements something that already works, or confidently reports something as broken when it isn't.

## Resolution

Verified each of the five tickets against current code on 2026-08-09 and confirmed all five fixes are genuinely present (not just plausible-looking):

- BLK-167 — `GraphVisualizationView.tsx` takes real props, no `SAMPLE_*` constants remain
- BLK-168 — `Pane2ExtractedData.tsx` gates the graph tab on real `runMeta.taskType`
- BLK-169 — `PnIDSkill` and graph tools are registered; `terminate_node` builds a graph result for `task_type == "graph_extraction"`
- BLK-171 — `terminate_node` forces `RunStatus.ERROR` on zero-token/zero-field runs
- BLK-172 — only `def-pnid-to-dexpi` exists in `prebuilt.py`

All five were moved from `backlog/bugs/` to `backlog/implemented/` with a `## Resolution` section added to each documenting what was checked.

## Acceptance Criteria

- [x] The five confirmed-fixed tickets are moved to `backlog/implemented/` with resolution evidence recorded
- [x] The mechanical backlog-cleanup pass for this batch is complete

## Constraints

- This is a process fix, not a code fix — the acceptance criteria above are about how tickets get closed going forward, not a runtime change
- Don't retroactively "fix" tickets by moving them without verifying against current code first (see the verification done above) — false closure is worse than staying open

## Dependencies

- None — this is bookkeeping, but informs how much weight to put on any other backlog file's `Status` field

## Notes

- Originally surfaced by a full-repo audit (`ADE_codebase_audit.md`, §5)
- This ticket itself is filed already-resolved (with the move done as part of filing it) since the fix was mechanical and low-risk
- Process norm going forward (not tracked as an open action item, just stated here): whoever lands a fix for a backlog ticket should move the ticket file and update its status in the same change, rather than leaving it to a later audit pass. A lightweight script that flags tickets whose described "problem" no longer matches the current code would catch this automatically — worth considering if this recurs
- This pass only verified the five tickets with clear code evidence (BLK-167/168/169/171/172); it is not a full audit of `backlog/bugs/`, `backlog/tech-debt/`, etc. — other open tickets have not been re-verified against current code and should still be treated as unconfirmed until checked

## Implementation Log

- **2026-08-09T09:50 (mgmt)**: Logged after full-repo audit flagged five tickets as stale-but-fixed.
- **2026-08-09T10:35 (mgmt)**: Verified all five against current code, moved to `backlog/implemented/` with resolution notes, closing this ticket's mechanical portion. Process-change acceptance criteria left open.
