---
id: BLK-203
type: bug
title: "Frontend templates page missing error handling and search — parity gap with skills and definitions pages"
priority: low
status: backlog
phase: 2
owner: antigravity
created: 2026-08-09T11:50:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, ux, consistency, error-handling]
---

## Description

The templates page at `frontend/app/templates/page.tsx` fetches data with no error handling:

```tsx
useEffect(() => {
    fetchTemplates().then(setTemplates);
}, []);
```

If the API is down or returns an error, this silently fails — `templates` stays as `[]` with no error message shown to the user. Compare to the skills page (`frontend/app/skills/page.tsx`) and definitions page (`frontend/app/definitions/page.tsx`), which both have proper error state:

```tsx
fetchSkills().then(setSkills).catch((e) => {
    setSkills([]);
    setError(e instanceof ApiError ? `API Error ${e.status}: ${e.message}` : String(e));
});
```

Additionally, the skills and definitions pages both have search/filter functionality (a search bar with `useMemo`-based filtering), but the templates page has none.

## Problem Statement

- A user who opens the Templates page when the backend is down sees an empty list with no explanation
- The templates page is the only registry page without search/filter, making it harder to find a specific template as the list grows (currently 19 prebuilt templates)
- This is a consistency issue — all three registry pages (definitions, skills, templates) should have the same UX patterns

## Acceptance Criteria

- [ ] Add error handling to `fetchTemplates()` call with error state and error display
- [ ] Add search/filter functionality matching the pattern used in skills and definitions pages
- [ ] Verify error state renders consistently with the other pages' error UI

## Constraints

- Follow the existing pattern from skills/definitions pages — don't introduce a new error handling approach
- Keep the search bar styling consistent with the other pages

## Dependencies

- `frontend/app/templates/page.tsx`
- `frontend/app/skills/page.tsx` (reference implementation)
- `frontend/app/definitions/page.tsx` (reference implementation)

## Notes

- Found during full-repo audit; the templates page appears to have been built first (simpler) and never updated when the other pages got error handling and search

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
