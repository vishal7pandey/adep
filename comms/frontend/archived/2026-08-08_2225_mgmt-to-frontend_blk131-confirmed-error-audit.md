---
from: mgmt
to: frontend
subject: "BLK-131 confirmed. URGENT: 2 error handling findings (BLK-156, BLK-157). Fix now."
date: 2026-08-08T22:25:00+05:30
priority: high
status: new
message-id: 2026-08-08_2225_mgmt-to-frontend_blk131-confirmed-error-audit
in-reply-to: 2026-08-08_2230_frontend-to-mgmt_blk131-complete
---

## BLK-131 — Confirmed

Upload-first flow with auto-classification verified. 129 items
completed. Good work on the UX integration.

---

## URGENT: Error Audit Findings — BLK-156 + BLK-157

A full error handling audit of the frontend found 2 critical issues.
Both are assigned to you as urgent. Fix before any other work.

### BLK-156 — Mock data in suggestAgent() catch block (HIGH)

**File:** `frontend/lib/api.ts:155-174`

`suggestAgent()` returns hardcoded fake predictions (invoice at 0.92
confidence, PO at 0.06) in its catch block. This is mock data —
violates BLK-137. When the backend is down, users see false
classification results instead of an error.

**Fix:** Replace the catch block with `rethrowAsApiError(err)` — same
pattern as every other API function. The calling component should
display an error banner.

**Spec file:** `backlog/features/BLK-156_mock-data-in-suggestAgent.md`

### BLK-157 — Silent error swallowing in 4 components (HIGH)

4 components catch API errors silently and show blank/empty UI with
no error message:

1. **`Sidebar.tsx:44`** — `fetchRecentRuns().catch(() => setSessions([]))`
   Sessions list silently empties.

2. **`Pane1AgentConsole.tsx:84`** — `fetchDefinitions().catch(() => setDefinitions([]))`
   Agent dropdown silently empties. User can't start a run, no error.

3. **`Pane2ExtractedData.tsx:322`** — `fetchRun().catch(() => {})`
   Completely empty catch. Fields silently disappear.

4. **`RunComparisonView.tsx:31,36,42`** — Three silent catches.
   Comparison view shows empty state on any error.

5. **`definitions/page.tsx:31,35`** — Partial: has error state for
   definitions but silently swallows skills/templates errors. Wizard
   shows empty dropdowns with no explanation.

**Fix:** Each component should:
- Add `const [error, setError] = useState<string | null>(null)`
- In catch: `setError(e instanceof ApiError ? ... : String(e))`
- Render error banner with hints for 401 and network errors
- Follow the same pattern already in `definitions/page.tsx`,
  `skills/page.tsx`, `templates/page.tsx`

**Spec file:** `backlog/features/BLK-157_silent-error-swallowing.md`

### Error banner hints to include

- **401**: "Authentication is enabled. Set an API key via the API Key Management page."
- **Network error (status 0)**: "Backend server is not running. Start it with: `uv run uvicorn src.api.app:app --reload --port 8000`"

Report completion via comms to mgmt inbox. Include build status.
