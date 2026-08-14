---
id: BLK-285
type: bug
title: "tsconfig.tsbuildinfo (140KB) committed to git — build artifact should be gitignored"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T13:05:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [garbage, git, frontend, build-artifacts, repo-hygiene]
---

## Description

`frontend/tsconfig.tsbuildinfo` (139,687 bytes) is committed to git. This is a TypeScript compiler incremental build cache file — it's regenerated on every `tsc` or `next build` run and should never be in version control.

The `frontend/.gitignore` file exists but doesn't include `*.tsbuildinfo` or `tsconfig.tsbuildinfo`.

## Problem Statement

- 140KB of build cache in git history permanently, for zero value
- The file changes on every build, creating noise in diffs and PRs
- It can cause false "modified" states in git status for developers
- Standard TypeScript projects gitignore this file

## Acceptance Criteria

- [ ] Add `*.tsbuildinfo` to `frontend/.gitignore`
- [ ] Remove `frontend/tsconfig.tsbuildinfo` from git tracking (`git rm --cached`)
- [ ] Verify the file is regenerated on next build and ignored by git

## Constraints

- None — this is a standard gitignore fix

## Dependencies

- `frontend/tsconfig.tsbuildinfo`
- `frontend/.gitignore`

## Notes

- Found during full-repo audit; the `.gitignore` in `frontend/` exists but missed this common TypeScript artifact

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
