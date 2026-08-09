---
id: BLK-114
type: feature
title: "Command palette (Ctrl+K / Cmd+K)"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:30:00+05:30
estimate: M
depends-on: []
tags: [frontend, ux, command-palette, power-users]
---

## Description

Global command palette triggered by Ctrl+K / Cmd+K for fast
navigation and actions.

## Commands

- "New session" → instant new extraction
- "Open run-001" → jump to specific run
- "Switch to Invoice Extractor" → change agent definition
- "Export results" → trigger JSON/CSV export
- "Toggle dark mode"
- Fuzzy search across sessions, agents, skills, templates

## Acceptance Criteria

- [ ] Ctrl+K / Cmd+K opens palette
- [ ] Escape closes palette
- [ ] Fuzzy search across sessions, definitions, skills, templates
- [ ] Arrow key navigation through results
- [ ] Enter executes selected command
- [ ] No backend dependency

## Source

Frontend proposal #1 in `2026-08-08_0425_frontend-to-mgmt_engineering-proposals.md`
