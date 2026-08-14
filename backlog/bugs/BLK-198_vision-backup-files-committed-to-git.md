---
id: BLK-198
type: bug
title: "Vision backup files (136KB) committed to git as garbage"
priority: low
status: backlog
phase: 2
owner: mgmt
created: 2026-08-09T11:25:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [garbage, git, docs, repo-hygiene]
---

## Description

Two backup copies of the vision document are committed to git:

- `vision.md.backup.md` — 56,994 bytes
- `vision.backup.20260809.md` — 79,395 bytes

The canonical `vision.md` is 82,998 bytes. The backups are point-in-time snapshots that serve no purpose in version control — that's what git history is for. They bloat the repo, clutter directory listings, and create confusion about which file is current.

## Problem Statement

- 136KB of backup files in git history permanently, for zero value
- `vision.md.backup.md` has a double extension (`.md.backup.md`) suggesting it was created manually and carelessly
- `vision.backup.20260809.md` has a date in the filename, which is redundant with git commit dates
- These files appear in searches, IDE file trees, and directory listings, adding noise

## Acceptance Criteria

- [ ] Delete both backup files
- [ ] Add `*.backup.*` and `*.bak` to `.gitignore` to prevent future backup file commits
- [ ] Verify no documentation or scripts reference either backup file

## Constraints

- None — git history preserves all prior versions of `vision.md`

## Dependencies

- None

## Notes

- Found during full-repo audit; classic "forgot to clean up after editing" pattern

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `mgmt` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
