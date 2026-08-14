---
id: BLK-262
type: bug
title: "Modals declare aria-modal but have no focus trap, no Escape close, no focus restoration — keyboard users can tab into background"
priority: medium
status: backlog
phase: 3
owner: antigravity
created: 2026-08-09T13:50:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, a11y, modal, focus-trap, keyboard, accessibility]
---

## Description

`frontend/components/ui/OnboardingTour.tsx` (lines ~108-109) and `frontend/components/ui/KeyboardShortcutsModal.tsx` (lines ~29-30) render `role="dialog"` with `aria-modal="true"` — but neither implements the rest of the modal contract:

- **No focus trap**: after opening, Tab can move focus to background page content (nothing restricts focus to the dialog). Keyboard users can "leave" the modal visually without knowing it.
- **No Escape key close** (OnboardingTour has no keydown handler; CommandPalette has one but the two dialogs don't).
- **No focus on open / no focus restoration on close** — the trigger element's focus is not returned after the modal closes.
- No `aria-labelledby`/`aria-describedby` wiring to the dialog title/description (title heading is present but not referenced).

## Problem Statement

`aria-modal="true"` tells screen readers the rest of the page is inert, but nothing enforces that in the DOM — a contract violation. Combined with no Escape/focus-restore, keyboard and screen-reader users get a stuck or escapable modal. This is a core a11y regression for first-run and shortcuts features.

## Acceptance Criteria

- [ ] Focus is trapped inside the open dialog (Tab/Shift+Tab cycle within the modal; inert or `aria-hidden` background)
- [ ] Escape closes the modal; close restores focus to the previously-focused element
- [ ] Modal announces its title via `aria-labelledby` (and description via `aria-describedby` where present)
- [ ] Reuse a single small focus-trap util (do not copy-paste); apply to both dialogs
- [ ] A test: Tab cycles within the dialog and never reaches background interactive elements

## Constraints

- Keep the existing tour step and shortcuts content unchanged
- Do not break CommandPalette's existing Escape behavior

## Dependencies

- `frontend/components/ui/OnboardingTour.tsx`
- `frontend/components/ui/KeyboardShortcutsModal.tsx`
- `frontend/components/ui/CommandPalette.tsx` (reference for existing Escape handling)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:50**: Filed after reading both dialog components — aria-modal present, focus-trap/Escape/focus-restore absent.