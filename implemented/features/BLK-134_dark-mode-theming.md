---
id: BLK-134
type: feature
title: "Dark mode + theme system"
priority: medium
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: []
tags: [frontend, ux, theming, dark-mode, accessibility]
---

## Problem

No dark mode. The command palette proposal (BLK-114) already assumes
a "Toggle dark mode" command exists, so the two are coupled.

Beyond preference: this is a document-analysis tool that people stare
at for hours. Dark mode is an eye-strain and accessibility concern,
not decoration.

## Requirements

### 1. Theme Tokens

Formalise the existing design system (BLK-055) into semantic CSS
custom properties rather than hardcoded colours:

```
--color-bg-primary / -secondary / -tertiary
--color-text-primary / -secondary / -muted
--color-border-default / -strong
--color-accent            (Electric Blue)
--color-success / -warning / -danger
--color-confidence-high / -medium / -low
```

Every component consumes tokens. No literal hex values in component
files.

### 2. Three Modes

- Light
- Dark
- System (follows `prefers-color-scheme`)

Persist the choice in localStorage. Apply before first paint to avoid
a flash of the wrong theme.

### 3. Document Viewer Consideration

**The document itself must not be inverted.** A scanned invoice
rendered in inverted colours is unreadable and changes what the user
is verifying.

- Chrome, toolbar, and panels: themed
- Document page render: always true-to-original
- Provide a subtle neutral mat around the page in dark mode so the
  white page isn't a harsh rectangle on black

### 4. Confidence Colour Integrity

The confidence colour scale (green/yellow/red) must retain sufficient
contrast in both themes. Dark mode typically needs desaturated,
lighter variants. Verify against WCAG contrast requirements in both
themes — this ties into BLK-117.

### 5. Bounding Box Overlays

Overlay colours (BLK-115 heatmap, active-field highlight) must remain
visible against both light document backgrounds and the dark chrome.
Test on a white scan and a dark photograph.

## Acceptance Criteria

- [ ] Semantic theme tokens defined; no hex literals in components
- [ ] Light, dark, and system modes
- [ ] Choice persisted; applied before first paint (no flash)
- [ ] Document page render never inverted
- [ ] Neutral mat around the page in dark mode
- [ ] Confidence colours meet WCAG contrast in both themes
- [ ] Bbox overlays visible on light and dark document content
- [ ] Command palette exposes a theme toggle (BLK-114 integration)
- [ ] All existing screens audited in both themes
- [ ] No component regressions in light mode

## Notes

Do this after BLK-114 (command palette) so the toggle has a natural
home, and coordinate with BLK-117 (a11y) so contrast is verified once
across both themes rather than twice.
