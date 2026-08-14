---
id: BLK-196
type: bug
title: "Misplaced app/ directory at repo root contains orphaned Next.js page"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T11:15:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [structure, garbage, frontend, scaffolding]
---

## Description

There is an `app/` directory at the **repo root** containing `templates/page.tsx` — a Next.js page component. The actual Next.js application lives under `frontend/app/`, which already has its own `templates/page.tsx`. The root-level `app/` directory is not part of any build, not referenced by any configuration, and is clearly a leftover from project scaffolding or a misplaced file copy.

## Problem Statement

- The root `app/templates/page.tsx` imports from `@/lib/api` and `@/components/ui/LttsButton` — path aliases that resolve relative to `frontend/`, not the repo root. This file would not compile if it were part of any build.
- It's confusing: a developer seeing `app/` at the repo root might think it's the Next.js app root, when the actual app is under `frontend/app/`
- It's dead code — no tooling, build, or test references it
- It adds noise to directory listings and searches

## Acceptance Criteria

- [ ] Delete the root-level `app/` directory entirely
- [ ] Verify no references to `./app/` or `app/templates/` exist in any config or script
- [ ] Confirm `frontend/app/templates/page.tsx` is the canonical version

## Constraints

- None — this is pure deletion of dead files

## Dependencies

- None

## Notes

- Found during full-repo audit; likely a leftover from when the project was initially scaffolded

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
