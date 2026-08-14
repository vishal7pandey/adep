---
id: BLK-201
type: tech-debt
title: "notebooks/ directory contains course notebooks unrelated to the platform"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T11:40:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [garbage, scope-creep, education, repo-hygiene]
---

## Description

The `notebooks/` directory contains 5 Jupyter notebooks:

- `L2.ipynb` (16KB)
- `L4.ipynb` (28KB)
- `L6.ipynb` (46KB)
- `L8.ipynb` (30KB)
- `L9.ipynb` (30KB)

These are course notebooks from a DeepLearning.AI course (the "L" prefix and incremental numbering are typical of course materials). They are not part of the ADEP platform — no source code imports them, no tests reference them, no documentation mentions them, and they don't contain platform-relevant prototypes or experiments.

## Problem Statement

- 150KB of course notebooks sit in a production repository with no connection to the platform
- They inflate the repo size and appear in searches and IDE file trees
- They suggest the repo was used as a personal learning workspace rather than a dedicated project
- The `ADE_codebase_audit.md` already flagged "significant scope creep from the original DeepLearning.AI course material" — these notebooks are the literal course material

## Acceptance Criteria

- [ ] Remove the `notebooks/` directory from the repo
- [ ] If any notebook contains prototype code that informed the platform design, extract that code into a proper `scripts/` or `docs/` artifact with context, then delete the notebook
- [ ] Add `*.ipynb` to `.gitignore` (except `notebooks/` if a deliberate notebooks directory is wanted — but currently it shouldn't be)

## Constraints

- None — these are not referenced by anything in the codebase

## Dependencies

- None

## Notes

- Found during full-repo audit; the audit report already noted the scope creep from course material

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
