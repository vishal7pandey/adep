---
id: BLK-286
type: tech-debt
title: "Frontend has 1 test file (1.4KB) for 21 components and 8 pages — near-zero test coverage"
priority: medium
status: backlog
phase: 2
owner: antigravity
created: 2026-08-09T13:10:00+05:30
started: null
completed: null
estimate: L
depends-on: []
tags: [frontend, testing, coverage, quality]
---

## Description

The frontend has 21 component files (`.tsx`) and 8 page files, plus 3 lib modules (`api.ts` 629 lines, `analytics.ts` 329 lines, `sse.ts` 232 lines) and 3 context providers. The entire test suite consists of:

- `frontend/tests/frontend/api.test.ts` — 1,435 bytes

That's one test file testing a fraction of the API client, for a frontend with ~3,500 lines of component code and ~1,200 lines of library code.

The CI pipeline runs `npm run lint` and `npm run build` for the frontend but has no test step (there's no `test` script in `package.json` either).

## Problem Statement

- No tests for any of the 21 components — workbench layout, agent console, extracted data panel, document viewer, graph visualization, run comparison, template editor, skill editor, AI template composer, settings, sidebar, error boundary, etc.
- No tests for the SSE client (`sse.ts`) — reconnection logic, event parsing, error handling are untested
- No tests for the analytics module (`analytics.ts`) — 329 lines of metric computation with no verification
- No tests for the context providers — `WorkbenchContext`, `ThemeContext`, `ActiveHighlightContext`
- No tests for page-level rendering, routing, or error states
- The single `api.test.ts` file is 1.4KB — it likely tests one or two API functions at most
- `package.json` has no `test` script, so even if tests existed, CI wouldn't run them

## Acceptance Criteria

- [ ] Add a `test` script to `frontend/package.json` (e.g., `vitest` or `jest`)
- [ ] Add test configuration (vitest config or jest config)
- [ ] Write tests for `lib/api.ts` — all API functions, error handling, auth header propagation
- [ ] Write tests for `lib/sse.ts` — connection, reconnection, event parsing, error handling
- [ ] Write tests for `lib/analytics.ts` — metric computation functions
- [ ] Write component tests for critical components: `WorkbenchLayout`, `Pane1AgentConsole`, `Pane2ExtractedData`, `Pane3DocumentViewer`
- [ ] Add frontend test step to CI (`ci.yml`)
- [ ] Target at least 40% coverage as a starting point

## Constraints

- Use Vitest (compatible with Next.js, Vite ecosystem) or Jest with Next.js plugin
- Don't block CI on coverage thresholds initially — just get tests running

## Dependencies

- `frontend/package.json` (add test script + test runner dependency)
- `.github/workflows/ci.yml` (add frontend test step)
- All frontend components and lib modules

## Notes

- Found during full-repo audit; the backend has 55 test files but the frontend has 1 — a stark asymmetry

## Implementation Log

- **2026-08-09T16:00 (mgmt)**: Reassigned from `cline` (mandate suspended, see projectmgmt/STATUS.md 2026-08-09 16:00 note) to `antigravity`. Test-code ownership for this file's domain reverts to the implementing team; independent verification now happens via cross-team review (devin<->antigravity) instead of a dedicated gate.

- **2026-08-09 (mgmt)**: Assigned to `cline` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
