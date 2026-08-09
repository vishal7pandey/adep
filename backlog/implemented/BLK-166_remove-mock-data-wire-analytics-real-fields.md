---
id: BLK-166
title: "Remove all mock/demo data fallbacks and wire analytics to real backend fields"
status: assigned
priority: high
estimate: M
assigned_to: frontend
created: 2026-08-09T00:25:00+05:30
by: mgmt
depends_on: [BLK-165]
---

## Problem

The frontend has residual mock/demo data in several places that
needs to be removed now that the backend is fully functional.
The analytics dashboard (BLK-119) also needs to be wired to the
new backend fields from BLK-165.

## Items to fix

### 1. Remove `generateMockRuns` fallback in analytics

**Files:** `lib/analytics.ts`, `app/analytics/page.tsx`

The analytics page falls back to `generateMockRuns(60)` when the
backend returns 0 runs or is unreachable. Remove this entirely.

**Replace with:** Pure empty state when 0 runs:
- "No runs yet — run an extraction to see analytics"
- No "Demo Data" badge
- No `usingMock` state
- No `generateMockRuns` function

When the backend is unreachable, show the error message (same
pattern as other pages).

### 2. Remove `sample_invoice.pdf` fallbacks

**File:** `components/workbench/Pane1AgentConsole.tsx`
- Line ~157: `setUploadedFileName(documentFileName || 'sample_invoice.pdf')`
- Line ~239: `const docUrl = documentUrl || uploadedFileName || documentFileName || 'sample_invoice.pdf'`

**File:** `components/workbench/RunComparisonView.tsx`
- Line ~126: `{r.id} ({r.document_url || 'sample_invoice.pdf'})`
- Line ~142: `{r.id} ({r.document_url || 'sample_invoice.pdf'})`

**Fix:** Remove the `|| 'sample_invoice.pdf'` fallback. If no
document is uploaded, the Start button should be disabled (it
already checks for uploaded file). For RunComparisonView, show
`r.document_url || '—'` or just `r.id`.

### 3. Extend `ExtractionRun` interface

**File:** `lib/api.ts`

Add fields from BLK-165:

```typescript
export interface ExtractionRun {
  id: string;
  definition_id: string;
  document_url: string;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'stopped';
  current_cycle: number;
  total_fields: number;
  extracted_fields_count: number;
  fields: ExtractedField[];
  // New from BLK-165:
  total_cost_usd?: number;
  total_tokens?: number;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}
```

### 4. Wire analytics charts to real cost/timestamp data

**File:** `lib/analytics.ts`

- **Cost per Day chart:** Use `run.total_cost_usd` instead of
  mock cost values. Filter out runs with no cost data (0 or
  undefined).
- **Processing Time Distribution chart:** Compute duration from
  `completed_at - started_at` (parse ISO strings). Filter out
  runs missing either timestamp.

### 5. Fix pre-existing eslint errors (optional, bonus)

The frontend dev flagged 15 pre-existing
`react-hooks/set-state-in-effect` eslint errors in
`ThemeContext.tsx`, `WorkbenchContext.tsx`, etc. These are from
React 19's stricter rules. Fix if time permits — not blocking.

## Acceptance Criteria

- [ ] `generateMockRuns` function removed from `lib/analytics.ts`
- [ ] No "Demo Data" badge or `usingMock` state in analytics page
- [ ] Empty state shown when 0 runs (not mock data)
- [ ] `sample_invoice.pdf` fallbacks removed from
      `Pane1AgentConsole.tsx` and `RunComparisonView.tsx`
- [ ] `ExtractionRun` interface extended with cost/token/timestamp
      fields
- [ ] Cost per Day chart uses `total_cost_usd` from real data
- [ ] Processing Time chart uses `completed_at - started_at`
- [ ] Build passes with 0 TypeScript errors
- [ ] No new eslint errors introduced

## Dependencies

- **BLK-165** (backend) must ship first — the cost/tokens/timestamps
  won't exist in run records until that's done. However, the mock
  data removal and interface extension can proceed in parallel.
  The charts will show empty/zero until BLK-165 is deployed.
