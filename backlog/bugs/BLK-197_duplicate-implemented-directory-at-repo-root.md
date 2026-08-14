---
id: BLK-197
type: bug
title: "Duplicate implemented/ directory at repo root shadows backlog/implemented/"
priority: low
status: backlog
phase: 2
owner: mgmt
created: 2026-08-09T11:20:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [structure, garbage, process, backlog]
---

## Description

There is an `implemented/` directory at the **repo root** with `bugs/` and `features/` subdirectories containing only `.gitkeep` files. The actual implemented backlog items live in `backlog/implemented/` which has 70+ properly filed markdown files. The root-level `implemented/` directory is empty, redundant, and confusing.

## Problem Statement

- Two `implemented/` directories exist: `implemented/` (root, empty) and `backlog/implemented/` (has all the real items)
- A developer or tool looking for implemented items might find the empty one first and conclude nothing has been done
- It suggests a process confusion — someone created the directory structure at the wrong level and never populated it

## Acceptance Criteria

- [ ] Delete the root-level `implemented/` directory
- [ ] Verify no scripts, configs, or documentation reference `./implemented/` (as opposed to `./backlog/implemented/`)

## Constraints

- None — pure deletion of empty redundant directories

## Dependencies

- None

## Notes

- Found during full-repo audit; the `backlog/` directory structure is the canonical one per `projectmgmt/PROCESS.md`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `mgmt` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
