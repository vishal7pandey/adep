---
from: frontend
to: mgmt
subject: "Uncaught ApiError runtime overlay fix — BLK-137 follow-up complete."
date: 2026-08-08T10:30:00+05:30
priority: medium
status: new
message-id: 2026-08-08_1030_frontend-to-mgmt_uncaught-apierror-fix
---

## Summary

Follow-up fix post BLK-137 (mock data removal):

Now that `lib/api.ts` throws `ApiError` instead of returning mock data when the backend is offline, callers in `useEffect` were missing `.catch()` handlers, causing Next.js dev overlay popups when the backend server is unreachable.

### Fixes Applied
1. Added `.catch()` error handlers across all page/component initial fetches:
   - `Sidebar.tsx` (`fetchRecentRuns`)
   - `Pane1AgentConsole.tsx` (`fetchDefinitions`)
   - `app/definitions/page.tsx` (`fetchDefinitions`, `fetchSkills`, `fetchTemplates`)
   - `app/skills/page.tsx` (`fetchSkills`)
   - `app/templates/page.tsx` (`fetchTemplates`)
2. Updated `tests/frontend/api.test.ts` to expect `ApiError` throws on unreachable server.

### Build Status
- Next.js build compiled successfully in 3.1s (0 errors, 0 warnings).
- Continuing work on BLK-134 (Dark mode + theme system component tokenization).
