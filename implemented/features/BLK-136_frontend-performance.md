---
id: BLK-136
type: feature
title: "Frontend performance — code splitting, bundle budget, virtualized lists"
priority: medium
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: []
tags: [frontend, performance, bundle-size, virtualization]
---

## Problem

No performance budget or measurement exists. Several known risks:

- The agent builder wizard, all three editors, and the admin dashboard
  are likely in the initial bundle even though most sessions never
  open them
- `react-flow` (BLK-112) and charting (BLK-119) are heavy and will be
  pulled in unconditionally if imported statically
- Long field lists, long traces, and long session lists render every
  row — a 200-field extraction or a 500-entry trace will stutter
- The document viewer holds full-resolution page images in memory with
  no eviction

## Requirements

### 1. Route-Level Code Splitting

Lazy-load routes that are not part of the core extraction path:

- `/definitions` wizard
- `/skills` editor
- `/templates` editor
- `/admin` dashboard
- `/analytics` (BLK-119)

Core workbench (3 panes) stays in the initial bundle. Show a skeleton
(BLK-132) during chunk load.

### 2. Heavy Dependency Isolation

- `react-flow` dynamically imported only when a graph extraction
  result is present
- Charting library dynamically imported only on the analytics route
- Syntax highlighter dynamically imported only when a serialized
  format tab is opened

### 3. Virtualized Lists

Use windowing for any list that can grow unbounded:

| List | Threshold |
|------|-----------|
| Pane 2 field cards | > 50 fields |
| Pane 1 trace entries | > 100 entries |
| Session list | > 100 sessions |
| Agent picker grid | > 50 agents |

Below the threshold, render normally — virtualization adds complexity
and should not be paid for when unnecessary.

### 4. Document Image Memory

- Keep at most N page images decoded (default 3: current, previous,
  next)
- Evict others; re-fetch on navigation
- Use the existing thumbnail endpoint for the page-strip rather than
  full-resolution images

### 5. Bundle Budget in CI

Enforce a budget so regressions are caught at PR time, not in
production:

| Metric | Budget |
|--------|--------|
| Initial JS (gzipped) | < 250 KB |
| Largest lazy chunk | < 400 KB |
| Total JS | < 1.5 MB |
| Lighthouse performance | > 85 |

Fail the frontend CI job on budget breach. Report the delta versus
main in the job output.

## Acceptance Criteria

- [ ] Route-level lazy loading for the 5 non-core routes
- [ ] Skeleton shown during chunk load
- [ ] `react-flow`, charts, and syntax highlighter dynamically imported
- [ ] Virtualized rendering above the 4 stated thresholds
- [ ] Non-virtualized path retained below thresholds
- [ ] Page image cache bounded to 3 decoded pages with eviction
- [ ] Page strip uses thumbnails, not full-resolution images
- [ ] Bundle budget enforced in CI with delta reporting
- [ ] Lighthouse performance > 85 on the workbench route
- [ ] Measured before/after numbers recorded in the completion report
- [ ] No functional regressions

## Notes

Do this **before** BLK-112 (graph visualization) and BLK-119
(analytics) land, so the heavy dependencies are introduced behind
dynamic imports from the start rather than retrofitted.

Report actual measured numbers on completion, not just "done" —
the point of a budget is the measurement.
