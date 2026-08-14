---
id: BLK-190
type: idea
title: "Add 'Copy to clipboard' and filename-based export for extracted data"
priority: low
status: backlog
phase: 5
owner: unassigned
created: 2026-08-09T11:05:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, ux, export, workbench]
---

## Description

The extraction workbench produces structured data (fields, JSON, CSV) but the primary interaction path is visual. Two small UX improvements would materially improve the local-first workflow:

1. **Copy-to-clipboard for extracted JSON** — one click copies the current run's extracted fields as JSON to the clipboard. Fast, no backend round-trip.
2. **Filename-based export naming** — when exporting a run as JSON/CSV (BLK-133), default the download filename to `{run_id}-{definition_id}.json` instead of a generic name, so users can identify exports without renaming.

## Why

- Reduces friction: most users want to paste extracted data into a spreadsheet or doc
- Improves organization: auto-named exports are easier to find later
- Fits the "local-first" vision: no server needed for clipboard

## Acceptance Criteria

- [ ] Copy button on Pane2 (Extracted Data) copies the current run's extracted JSON to clipboard
- [ ] Export endpoints (or frontend blob handling) use a meaningful download filename derived from run ID + definition
- [ ] Clipboard copy works in Chrome/Edge/Firefox
- [ ] No backend change required for copy-to-clipboard (client-side only)

## Constraints

- Must not leak data to external services (clipboard stays local)
- Export filename should stay within safe filesystem name rules (no slashes, no reserved chars)

## Dependencies

- None

## Notes

- Found during frontend UX audit
- Related to BLK-133 (export endpoints) and BLK-135 (local API key storage)