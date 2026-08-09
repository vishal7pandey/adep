---
id: BLK-029
type: feature
title: "Skill Editor — structured form for creating/editing skills"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-027]
tags: [frontend, skill-editor, ui]
---

## Description

Build the Skill Editor — accessible from the sidebar as a modal or page.
Structured form UI for creating, editing, and cloning skills. Users adjust
system prompts, tool preferences, probe order, invariants, failure actions,
and semantic check toggles without writing code.

## Acceptance Criteria

- [ ] List view: all skills with name, description, edit/delete actions
- [ ] Editor form: system prompt (textarea), tool preferences (multi-select)
- [ ] Probe order: drag-and-drop sortable list
- [ ] Invariants: add/remove/edit math rules (field_a, operator, field_b, tolerance)
- [ ] Failure actions: table mapping GapType → candidate action
- [ ] Known failure modes: add/remove text entries
- [ ] Save/clone/delete actions
- [ ] Form validation

## Dependencies

- BLK-027 (API client)

## Notes

- vision.md §0.2 (Skill Editor), §7.2 criterion 9
