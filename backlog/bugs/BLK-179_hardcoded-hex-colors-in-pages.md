---
id: BLK-179
type: bug
title: "Hardcoded hex colors still present in frontend pages despite BLK-134 tokenization claim"
priority: medium
status: backlog
phase: 5
owner: antigravity
created: 2026-08-09T10:10:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, theme, tokenization, regression]
---

## Description

BLK-134 claimed "100% tokenization, 0 hardcoded hex values remaining." However, a fresh audit finds hardcoded hex colors in multiple frontend pages:

- `frontend/app/analytics/page.tsx` — `COLORS` object contains `'#0071CE'`, `'#00B5E2'`, `'#4DB848'`, `'#F5BD1E'`, `'#DC3545'`, `'#A27CC9'`, `'#00205C'`
- `frontend/app/definitions/page.tsx` — `text-[#0071CE]`, `border-[#0071CE]`, `bg-[#0071CE]/10`, `ring-[#0071CE]/40`, `bg-[#A27CC9]`, `border-[#A27CC9]`
- `frontend/app/skills/page.tsx` — `text-[#0071CE]`, `border-[#0071CE]`, `hover:border-[#0071CE]`
- `frontend/app/templates/page.tsx` — `text-[#0071CE]`, `border-[#0071CE]`, `hover:border-[#0071CE]`

This breaks dark mode override and theme consistency, and contradicts the completed BLK-134 claim.

## Root Cause

BLK-134 tokenized components under `components/workbench/` and `components/ui/` but did not cover the route pages in `frontend/app/` (`analytics`, `definitions`, `skills`, `templates`). These pages were written after the tokenization pass and never converted.

## Files Affected

- `frontend/app/analytics/page.tsx` — COLORS object (lines 40-48)
- `frontend/app/definitions/page.tsx`
- `frontend/app/skills/page.tsx`
- `frontend/app/templates/page.tsx`

## Acceptance Criteria

- [ ] Replace all `#0071CE` with a `--brand-primary` CSS variable reference
- [ ] Replace all `#00B5E2`, `#4DB848`, `#F5BD1E`, `#DC3545`, `#A27CC9`, `#00205C` with existing CSS variables
- [ ] `grep -r '#[0-9a-fA-F]' frontend/app/` returns 0 results after fix
- [ ] Build is clean, `npm run build` passes

## Constraints

- Must not change the visual appearance for existing light/dark themes
- Must align with the color tokens already established in `globals.css`

## Dependencies

- None

## Notes

- This is a regression against the BLK-134 acceptance criteria ("0 hardcoded hex values remaining")
- Also relevant to BLK-149 which claimed "hex colors tokenized to CSS vars"

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
