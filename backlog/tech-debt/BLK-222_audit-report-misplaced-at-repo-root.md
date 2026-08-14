---
id: BLK-222
type: tech-debt
title: "ADE_codebase_audit.md at repo root is an audit report that should be in projectmgmt/ or docs/"
priority: low
status: backlog
phase: 2
owner: mgmt
created: 2026-08-09T13:30:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [structure, docs, repo-hygiene, audit]
---

## Description

`ADE_codebase_audit.md` (190 lines) is a critical codebase audit report that sits at the repo root. It's referenced by `projectmgmt/STATUS.md` and contains findings that overlap with the backlog. It's not referenced by README.md or CONTRIBUTING.md.

The repo root already has too many markdown files (README, CHANGELOG, CONTRIBUTING, vision.md, plus the 3 design docs flagged in BLK-206). The audit report belongs in `projectmgmt/` alongside `STATUS.md`, `PROCESS.md`, and `audit-ledger.md`.

## Problem Statement

- A critical audit report is buried at the repo root instead of being in the project management directory where stakeholders would look for it
- The file is referenced by `projectmgmt/STATUS.md` but lives outside that directory, creating a cross-directory dependency
- It adds to the repo root clutter (8+ markdown files at root)

## Acceptance Criteria

- [ ] Move `ADE_codebase_audit.md` to `projectmgmt/ADE_codebase_audit.md`
- [ ] Update any references to the old path in `projectmgmt/STATUS.md` or other files
- [ ] Or, if the audit findings are now fully captured in backlog items (BLK-193 through BLK-222), consider deleting the file and noting in `projectmgmt/STATUS.md` that the audit findings have been filed as backlog items

## Constraints

- Don't lose the content — if deleting, ensure all findings are captured in backlog items first

## Dependencies

- `ADE_codebase_audit.md`
- `projectmgmt/STATUS.md` (references the audit)
- Related to BLK-206 (design docs at repo root)

## Notes

- Found during full-repo audit; this file was the starting point for the current audit session and its findings have now been expanded into formal backlog items

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `mgmt` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
