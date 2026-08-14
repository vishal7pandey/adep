---
id: BLK-261
type: bug
title: "Onboarding 'Don't show again' checkbox is a no-op — tour always reopens and always marks seen"
priority: medium
status: backlog
phase: 3
owner: antigravity
created: 2026-08-09T13:45:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, onboarding, tour, ux, bug]
---

## Description

`frontend/components/onboarding/OnboardingTour.tsx` (lines ~62-63, ~99-102):

- `handleClose` always writes `localStorage.setItem('adep_tour_seen', 'true')` regardless of the "Don't show again" toggle state.
- The toggle's value is never read anywhere; checking the box has zero effect.
- Conversely, closing the tour by any means always marks it seen, so the checkbox implies an opt-out that can never actually be toggled per-user.

## Problem Statement

The onboarding tour is a first-run feature; its whole UX is built around "show once, let me opt out." Both halves are broken: users who uncheck can't get the tour again, and users who want to dismiss forever get it forever (until the stored key is removed). The stored flag is also global, not per-user (no account model yet, so acceptable), but the toggle semantics are simply wrong.

## Acceptance Criteria

- [ ] "Don't show again" checked → close sets `adep_tour_seen=true` and never reopens
- [ ] "Don't show again" unchecked → close sets `adep_tour_seen=false` (or a distinct dismiss-flag) so the tour can be replayed
- [ ] A test: check+close → not shown on next mount; uncheck+close → shown on next mount
- [ ] Ensure closing via other paths (X, outside click) uses the same logic consistently

## Constraints

- Keep the tour content and step data unchanged
- No breaking changes to the localStorage key unless versioned

## Dependencies

- `frontend/components/onboarding/OnboardingTour.tsx`
- `frontend/context/*`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:45**: Filed after reading handleClose and the unused toggle.