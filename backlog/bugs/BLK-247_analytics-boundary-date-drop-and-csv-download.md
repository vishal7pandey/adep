---
id: BLK-247
type: bug
title: "Analytics date-range filter drops boundary-day runs; CSV export download silently fails in some browsers"
priority: medium
status: backlog
phase: 3
owner: antigravity
created: 2026-08-09T12:35:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, analytics, date-filter, export, csv, correctness]
---

## Description

Two defects in the frontend analytics layer:

1. **Date-range boundary bug** — `applyFilters` in `frontend/lib/analytics.ts` (~lines 105-114) compares `created_at` against `from`/`to` `Date` objects that carry the *current wall-clock time*. The "last 30d" / "90d" buckets start/end at mid-day boundaries, so runs created earlier on the boundary day are silently dropped from charts and KPIs. The range should clamp `from` to start-of-day and `to` to end-of-day.

2. **CSV download may silently fail** — `app/analytics/page.tsx` (~lines 249-254) calls `a.click()` then `URL.revokeObjectURL(url)` without appending the anchor to the DOM. Several browsers (older Firefox/Edge, some Safari) ignore `.click()` on detached anchors, so the download never fires. `Pane2` does `appendChild` before `.click()` correctly; analytics does not.

## Problem Statement

- Users see charts that are subtly wrong (boundary-day runs missing) without any indication.
- The "Download CSV" action appears to do nothing in affected browsers — no error, no file.

## Acceptance Criteria

- [ ] `from`/`to` filters are date-normalized (start-of-day / end-of-day) so boundary-day runs are included
- [ ] Regression test: a run at `from` day 00:01 and at `to` day 23:59 are both included in the "30d" range
- [ ] Analytics CSV export appends the anchor to the document before clicking (and removes it after), matching the working Pane2 pattern
- [ ] Both fixed behaviors are covered by a unit test

## Constraints

- Preserve the semantics of explicit user-picked exact dates (if a user picks an exact timestamp range, honor it) — only auto-clamp preset ranges

## Dependencies

- `frontend/lib/analytics.ts`
- `frontend/app/analytics/page.tsx`

## Notes

- Same class of boundary bug as calendar/timezone issues fixed in BLK-140; keep date math in one util to avoid drift.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T12:35 (mgmt)**: Filed from audit of analytics date handling and download helper.
