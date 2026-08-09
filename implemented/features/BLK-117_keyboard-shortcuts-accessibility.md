---
id: BLK-117
type: feature
title: "Keyboard shortcuts and accessibility (a11y)"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:30:00+05:30
estimate: L
depends-on: []
tags: [frontend, ux, accessibility, a11y, keyboard, wcag]
---

## Description

Full keyboard navigation support and WCAG 2.1 AA accessibility
compliance.

## Requirements

### Keyboard Shortcuts
- `Escape` → close modals, dropdowns, wizard
- `Enter` → confirm/submit in focused context
- `Tab` navigation through all interactive elements
- `Arrow keys` for cycling through field cards in Pane 2
- `1/2/3` → switch disclosure levels (Summary/Detailed/Expert)
- `Space` → pause/resume active run
- `?` → keyboard shortcut help modal

### Accessibility
- ARIA labels on all buttons, badges, cards
- Focus rings on interactive elements (currently suppressed by
  `focus:outline-none`)
- Skip navigation link for screen readers
- WCAG 2.1 AA compliance audit

## Acceptance Criteria

- [ ] All keyboard shortcuts implemented and documented
- [ ] Shortcut help modal accessible via `?`
- [ ] ARIA labels on all interactive elements
- [ ] Focus rings visible on all interactive elements
- [ ] Tab navigation follows logical order
- [ ] Screen reader test passes (NVDA or VoiceOver)
- [ ] No backend dependency

## Source

Frontend proposal #6 in `2026-08-08_0425_frontend-to-mgmt_engineering-proposals.md`

## Notes

This overlaps with existing BLK-057 (accessibility audit) and
BLK-062 (keyboard shortcuts). Those items should be superseded by
this more comprehensive item.
