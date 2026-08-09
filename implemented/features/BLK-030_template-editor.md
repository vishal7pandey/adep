---
id: BLK-030
type: feature
title: "Template Editor — schema builder UI for Pydantic templates"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-027]
tags: [frontend, template-editor, ui]
---

## Description

Build the Template Editor — a schema builder UI for creating, editing, and
cloning templates. Users define fields, types, descriptions, constraints,
and confidence thresholds through a visual form.

## Acceptance Criteria

- [ ] List view: all templates with name, field count, edit/delete actions
- [ ] Field builder: add/remove/reorder fields
- [ ] Per-field: name, type (str/int/float/date/list/nested), description, constraints
- [ ] Confidence threshold per field (slider or number input)
- [ ] Nested schema support (e.g., LineItem within InvoiceTemplate)
- [ ] Live preview of the Pydantic schema
- [ ] Save/clone/delete actions
- [ ] Form validation

## Dependencies

- BLK-027 (API client)

## Notes

- vision.md §0.2 (Template Editor), §7.2 criterion 10
