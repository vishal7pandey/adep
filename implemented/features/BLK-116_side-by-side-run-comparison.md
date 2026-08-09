---
id: BLK-116
type: feature
title: "Side-by-side run comparison"
priority: medium
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:30:00+05:30
estimate: L
depends-on: []
tags: [frontend, ux, comparison, iterative-tuning]
---

## Description

A "Compare Runs" view accessible from the session list for
field-by-field comparison of two extraction runs.

## Requirements

- Select 2 runs from sidebar → opens diff view
- Field-by-field comparison table:
  - Field name | Run A value | Run B value | Delta confidence
  - Green highlight for improvements, Red for regressions
- Summary stats: total confidence delta, fields changed, new fields
  found/lost
- Side-by-side document viewer showing both bbox sets

## Acceptance Criteria

- [ ] Compare view accessible from session list
- [ ] Field-by-field diff table with color coding
- [ ] Summary stats panel
- [ ] Side-by-side document viewer with both bbox sets
- [ ] No backend dependency — works with existing run data

## Source

Frontend proposal #4 in `2026-08-08_0425_frontend-to-mgmt_engineering-proposals.md`
