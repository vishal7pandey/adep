---
id: BLK-289
type: tech-debt
title: "238 comms/ files committed to git — multi-agent communication logs are runtime artifacts, not source code"
priority: low
status: backlog
phase: 2
owner: mgmt
created: 2026-08-09T13:25:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [garbage, git, comms, repo-hygiene, process]
---

## Description

The `comms/` directory contains 238 tracked files — multi-agent communication logs, protocol documents, RACI matrices, and message files organized by agent (backend, frontend, mgmt) with inbox/active/archive subdirectories. Examples:

- `comms/backend/active/2026-08-08_2305_mgmt-to-backend_blk129-directed.md`
- `comms/backend/active/2026-08-09_0045_mgmt-to-backend_blk165-confirmed-phase5-blk070-067-assigned.md`

These are operational communication records between AI agents (mgmt, backend, frontend) — they're the equivalent of Slack logs or email threads. They're not source code, not configuration, and not documentation that helps a developer understand the system.

The `.dockerignore` already excludes `comms/`, recognizing that these files don't belong in the Docker image. But they're still in git.

## Problem Statement

- 238 files of agent-to-agent messages bloat the repo and git history
- These are timestamped operational artifacts — they have no value beyond the moment they were sent
- They clutter directory listings, searches, and IDE file trees
- The `comms/PROTOCOL.md` and `comms/RACI.md` documents might have value, but the 230+ message files do not
- This is the same class of issue as BLK-191 (runtime artifacts committed to git) and BLK-198 (backup files committed)

## Acceptance Criteria

- [ ] Keep `comms/PROTOCOL.md`, `comms/RACI.md`, and `comms/README.md` (process documentation)
- [ ] Remove all message files (`comms/*/active/*.md`, `comms/*/archived/*.md`, `comms/*/inbox/*.md`)
- [ ] Add `comms/*/active/` and `comms/*/archived/` and `comms/*/inbox/` to `.gitignore` (keep `.gitkeep` files for directory structure)
- [ ] Or, if the comms history is valuable as an audit trail, move it to a separate `comms-archive/` branch or a wiki

## Constraints

- Don't delete `comms/PROTOCOL.md`, `comms/RACI.md`, or `comms/README.md` — these define the communication process
- Keep `.gitkeep` files so the directory structure is preserved for future use

## Dependencies

- `comms/` directory (238 files)
- `.gitignore`
- Related to BLK-191 (runtime artifacts committed) and BLK-198 (backup files committed)

## Notes

- Found during full-repo audit; the `.dockerignore` already excludes `comms/`, acknowledging these aren't needed in production — but they shouldn't be in git either

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `mgmt` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
