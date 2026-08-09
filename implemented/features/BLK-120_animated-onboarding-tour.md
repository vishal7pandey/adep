---
id: BLK-120
type: feature
title: "Animated onboarding tour"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:30:00+05:30
estimate: M
depends-on: []
tags: [frontend, ux, onboarding, adoption, first-run]
---

## Description

First-time user onboarding flow that guides new users through the
platform's key concepts and 3-pane layout.

## Requirements

- Step 1: "Welcome to ADEP" overlay → explains the platform purpose
- Step 2: Highlight sidebar → "Choose or build an extraction agent"
- Step 3: Highlight upload button → "Upload your document here"
- Step 4: Demo run plays automatically with sample invoice
- Step 5: Highlight Pane 2 → "See extracted data appear in real-time"
- Step 6: Highlight Pane 3 → "Click any field to see where it was
  found in the document"
- Dismissible, with "Don't show again" checkbox
- Accessible via "Help → Take a tour" menu item
- Use localStorage for "seen" state

## Acceptance Criteria

- [ ] 6-step onboarding tour with visual highlights
- [ ] Demo run with sample invoice (pre-recorded or live)
- [ ] "Don't show again" persistence via localStorage
- [ ] Re-triggerable via Help menu
- [ ] No backend dependency

## Source

Frontend proposal #8 in `2026-08-08_0425_frontend-to-mgmt_engineering-proposals.md`
