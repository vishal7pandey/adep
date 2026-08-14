---
from: mgmt
to: frontend
subject: "BLK-119 CONFIRMED. Next: BLK-166 — remove all mock/demo data."
date: 2026-08-09T00:25:00+05:30
priority: high
status: done
message-id: 2026-08-09_0025_mgmt-to-frontend_blk119-confirmed-blk166-assigned
in-reply-to: 2026-08-09_0030_frontend-to-mgmt_blk119-complete
---

## BLK-119 — Confirmed

Great work on the analytics dashboard. All acceptance criteria met:
- `/analytics` route with 6 charts ✓
- Date range + agent + doc type filters ✓
- Data computed client-side from `/runs` ✓
- Charts render with 50+ runs ✓
- CSV/PDF export ✓
- Sidebar nav added ✓
- Build clean, 0 TypeScript errors ✓

Thanks for flagging the demo data fallback and pre-existing eslint
errors. Acting on both below.

## Next assignment: BLK-166 (M, urgent)

**BLK-166 — Remove all mock/demo data, wire analytics to real fields**

Spec: `backlog/features/BLK-166_remove-mock-data-wire-analytics-real-fields.md`

### 1. Remove `generateMockRuns` fallback

Remove the `generateMockRuns()` function from `lib/analytics.ts`
and all usage in `app/analytics/page.tsx`. When backend returns 0
runs, show a pure empty state: "No runs yet — run an extraction
to see analytics." When backend is unreachable, show the error
message (same pattern as other registry pages).

No "Demo Data" badge. No `usingMock` state.

### 2. Remove `sample_invoice.pdf` fallbacks

**`Pane1AgentConsole.tsx`:**
- Line ~157: Remove `|| 'sample_invoice.pdf'` from
  `setUploadedFileName()`
- Line ~239: Remove `|| 'sample_invoice.pdf'` from docUrl fallback
  chain

**`RunComparisonView.tsx`:**
- Lines ~126, ~142: Change `r.document_url || 'sample_invoice.pdf'`
  to `r.document_url || '—'`

### 3. Extend `ExtractionRun` interface

Add to `lib/api.ts`:
```typescript
total_cost_usd?: number;
total_tokens?: number;
created_at?: string;
started_at?: string;
completed_at?: string;
```

These fields will be populated by backend BLK-165 (assigned in
parallel). The interface extension and mock data removal can
proceed immediately — the charts will show empty/zero until
BLK-165 deploys.

### 4. Wire charts to real data

- **Cost per Day**: Use `run.total_cost_usd`. Filter runs with
  no cost data.
- **Processing Time Distribution**: Compute from
  `completed_at - started_at` (parse ISO strings). Filter runs
  missing either timestamp.

### 5. Pre-existing eslint errors (bonus, not blocking)

The 15 `react-hooks/set-state-in-effect` errors in
ThemeContext.tsx, WorkbenchContext.tsx, etc. — fix if time
permits. Not blocking for this task.

### Dependency note

BLK-165 (backend, persist cost/tokens/timestamps) is assigned in
parallel. Your interface changes and mock removal are not blocked
— proceed immediately. The cost/time charts will just show empty
data until BLK-165 ships.

After BLK-166, we'll plan BLK-118 (batch processing) jointly with
backend.

## Resolution

BLK-166 completed. All mock/demo data removed from the frontend.

- `generateMockRuns()` and all mock constants deleted from
  `lib/analytics.ts`. `getMeta()` rewritten to use real
  `ExtractionRun` fields (`created_at`, `total_cost_usd`,
  `total_tokens`, `started_at`/`completed_at`).
- `usingMock` state, "Demo Data" badge, and demo footer note
  removed from analytics page. Pure empty state added for 0 runs.
- `sample_invoice.pdf` fallbacks removed from
  `Pane1AgentConsole.tsx` (2 occurrences) and
  `RunComparisonView.tsx` (2 occurrences).
- `ExtractionRun` interface extended with 5 optional fields:
  `total_cost_usd`, `total_tokens`, `created_at`, `started_at`,
  `completed_at`.
- Cost per Day chart uses `total_cost_usd` (filters runs with
  no cost data). Processing Time chart uses `completed_at -
  started_at` (filters runs missing timestamps).
- Fixed unsafe non-null assertion in `computeAgentLeaderboard`.

Build: tsc 0 errors, eslint 0 errors on changed files, dev
server serves /analytics HTTP 200. Cost/time charts will
populate automatically once backend BLK-165 deploys.

Completion report sent to mgmt inbox:
`2026-08-09_0045_frontend-to-mgmt_blk166-complete.md`
