---
id: BLK-260
type: bug
title: "Dark-mode theme applies only post-mount — light flash (FOUC) on every load and SSR mismatches"
priority: medium
status: backlog
phase: 3
owner: antigravity
created: 2026-08-09T13:40:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, theme, dark-mode, FOUC, hydration, a11y, ux]
---

## Description

`frontend/context/ThemeContext.tsx` (lines ~14-30) adds the `dark` class to `document.documentElement` only inside a post-mount `useEffect`. `app/layout.tsx` (~lines 25-26) sets `suppressHydrationWarning` on `<html>`/`<body>`. Consequences:

- Dark-mode users see a bright flash on every page load (class applied after first paint).
- SSR always renders light HTML, then React re-paints dark — a visible theme switch and potential hydration mismatch (masked by `suppressHydrationWarning`).

## Problem Statement

FOUC on load is a polish/a11y regression in a feature the team already shipped (BLK-134 dark mode). The fix is the standard one: an inline blocking script in `<head>` that reads the stored theme (localStorage / media query) and sets the class before first paint, plus honoring the stored value server-side via a cookie or `<html>` attribute.

## Acceptance Criteria

- [ ] Theme class is applied before first paint (no flash) for both light and dark users
- [ ] Stored preference survives reload and is consistent with the media-query default
- [ ] No hydration mismatch warnings in the console (rely on the pre-paint script, not just `suppressHydrationWarning`)
- [ ] Consider `next-themes` or a minimal inline-script equivalent; keep the token system intact

## Constraints

- Keep the existing dark/light token set and the toggle UX
- Must work when JS is disabled (respect `prefers-color-scheme`) — progressive enhancement

## Dependencies

- `frontend/context/ThemeContext.tsx`
- `frontend/app/layout.tsx`
- `frontend/lib/*` theme store

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:40**: Filed after reading ThemeContext mount-time application.