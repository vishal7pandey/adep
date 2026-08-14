---
id: BLK-206
type: tech-debt
title: "Three standalone design docs (ADE industry mapping, Agentic UIUX, agentic agent builder) at repo root with no integration into project docs"
priority: low
status: backlog
phase: 2
owner: mgmt
created: 2026-08-09T12:05:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [docs, structure, repo-hygiene, scope-creep]
---

## Description

Three large markdown files sit at the repo root with no connection to the project's documentation structure:

- `ADE industry mapping.md` (27,556 bytes) — industry sector mapping document
- `Agentic UIUX Audit Heuristics.md` (35,797 bytes) — UI/UX audit heuristics
- `agentic agent builder.md` (29,412 bytes) — agent builder design document

These are not referenced by README.md, CONTRIBUTING.md, CHANGELOG.md, or any backlog item. They're not in a `docs/` directory. They have inconsistent naming (spaces in filenames, mixed case, no standard prefix). They appear to be design/planning documents that were dumped at the repo root and never integrated into the project's documentation structure.

## Problem Statement

- 93KB of design documents at the repo root with no discoverability — a new contributor wouldn't know they exist or how they relate to the project
- The filenames use spaces, which is inconsistent with the rest of the repo's naming conventions (kebab-case for backlog items, standard markdown names for docs)
- They may contain valuable design context, but their placement makes them invisible to anyone who doesn't browse the root directory
- They contribute to the "scope creep" appearance noted in `ADE_codebase_audit.md` — the repo looks like a dumping ground for unrelated planning documents

## Acceptance Criteria

- [ ] Move all three files into a `docs/` directory (create one if it doesn't exist)
- [ ] Rename to use consistent kebab-case: `ade-industry-mapping.md`, `agentic-uiux-audit-heuristics.md`, `agentic-agent-builder.md`
- [ ] Add references to these documents in README.md or CONTRIBUTING.md under a "Design Documents" section
- [ ] Or, if any document is obsolete or superseded by `vision.md`, delete it and note the deletion in the commit message

## Constraints

- Don't lose any content — these may contain valuable design rationale
- If moving, update any internal cross-references

## Dependencies

- None

## Notes

- Found during full-repo audit; the repo root has 8 markdown files, which is too many for a project with a `projectmgmt/` directory and a `backlog/` directory that should hold most non-code documentation

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `mgmt` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
