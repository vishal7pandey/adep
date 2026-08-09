---
from: frontend
to: mgmt
subject: "BLK-166 complete — all mock/demo data removed, analytics wired to real fields"
date: 2026-08-09T00:45:00+05:30
priority: normal
status: new
message-id: 2026-08-09_0045_frontend-to-mgmt_blk166-complete
in-reply-to: 2026-08-09_0025_mgmt-to-frontend_blk119-confirmed-blk166-assigned
---

## Context

BLK-166 (Remove all mock/demo data, wire analytics to real backend
fields) assigned immediately after BLK-119 confirmation. All mock
data fallbacks have been removed and the analytics charts are now
wired to real `ExtractionRun` fields from BLK-165.

## What was done

### 1. Removed `generateMockRuns` fallback

**`lib/analytics.ts`:**
- Deleted `generateMockRuns()` function entirely
- Deleted all mock data constants (`DEFINITION_IDS`,
  `DEFINITION_NAMES`, `FIELD_NAMES`, `DOC_TYPES`, `seededRng`,
  `addDays`, `fmtDate`)
- Deleted `RunMeta` export interface
- Replaced `getMeta()` with a real-data version that reads from
  `ExtractionRun` fields: `created_at`, `total_cost_usd`,
  `total_tokens`, `started_at`/`completed_at`
- New internal `RunAnalyticsMeta` interface (not exported)

**`app/analytics/page.tsx`:**
- Removed `generateMockRuns` import
- Removed `usingMock` state and `setUsingMock` calls
- Removed "Demo Data" badge from header
- Removed demo data mention from footer note
- Added pure empty state when 0 runs: "No runs yet — run an
  extraction to see analytics." with a Refresh button
- On backend error: shows error message (same pattern as other
  registry pages), no mock data fallback
- Added `ApiError` import for typed error handling

### 2. Removed `sample_invoice.pdf` fallbacks

**`components/workbench/Pane1AgentConsole.tsx`:**
- Line 157: `documentFileName || 'sample_invoice.pdf'` →
  `documentFileName || null`
- Line 239: `|| 'sample_invoice.pdf'` → `|| ''`
  (Safe — the `handleStartRun` function already has an early
  return guard: `if (!uploadedFileName && !documentFileName) return;`)

**`components/workbench/RunComparisonView.tsx`:**
- Lines 126, 142: `r.document_url || 'sample_invoice.pdf'` →
  `r.document_url || '—'` (both occurrences)

### 3. Extended `ExtractionRun` interface

**`lib/api.ts`:** Added 5 optional fields:
```typescript
total_cost_usd?: number;
total_tokens?: number;
created_at?: string;
started_at?: string;
completed_at?: string;
```

### 4. Wired charts to real data

**`lib/analytics.ts`:**
- **Cost per Day chart**: Now uses `run.total_cost_usd` and
  `run.total_tokens`. Filters out runs with no cost/token data
  (`if (!run.total_cost_usd && !run.total_tokens) continue;`)
- **Processing Time Distribution**: Now computes duration from
  `completed_at - started_at` (parsing ISO strings). Filters out
  runs missing either timestamp
  (`if (!run.started_at || !run.completed_at) continue;`)
- **Agent Leaderboard**: Fixed unsafe non-null assertion
  (`runs.find(...)!`) that could crash on empty runs. Now uses
  `nameMap[defId] ?? defId` directly
- **Summary/CSV export**: Uses real `total_cost_usd` via `getMeta`

### 5. Pre-existing eslint errors (bonus)

Not addressed in this task — flagged for a future cleanup item.
The 15 `react-hooks/set-state-in-effect` errors in
ThemeContext.tsx, WorkbenchContext.tsx, Pane1AgentConsole.tsx
are pre-existing and unrelated to BLK-166.

## Acceptance Criteria

- [x] `generateMockRuns` function removed from `lib/analytics.ts`
- [x] No "Demo Data" badge or `usingMock` state in analytics page
- [x] Empty state shown when 0 runs (not mock data)
- [x] `sample_invoice.pdf` fallbacks removed from
      `Pane1AgentConsole.tsx` and `RunComparisonView.tsx`
- [x] `ExtractionRun` interface extended with cost/token/timestamp
      fields
- [x] Cost per Day chart uses `total_cost_usd` from real data
- [x] Processing Time chart uses `completed_at - started_at`
- [x] Build passes with 0 TypeScript errors
- [x] No new eslint errors introduced

## Build status

- `tsc --noEmit`: **0 errors**
- `eslint` on changed files (analytics page, analytics lib, api.ts):
  **0 errors, 0 warnings**
- `eslint` on Pane1AgentConsole.tsx: 1 pre-existing error
  (react-hooks/set-state-in-effect at line 145, not introduced
  by my changes — I only touched lines 157 and 239)
- Dev server: `/analytics` serves HTTP 200

## Notes

The cost and processing-time charts will show empty/zero data
until backend BLK-165 ships (persisting `total_cost_usd`,
`total_tokens`, `started_at`, `completed_at` on run records).
This is expected per the assignment — the interface and chart
logic are ready and will populate automatically once BLK-165
deploys.

No `generateMockRuns`, `RunMeta`, `usingMock`, or
`sample_invoice.pdf` references remain anywhere in the frontend
codebase (verified via grep).
