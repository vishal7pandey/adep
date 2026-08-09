---
id: BLK-148
type: bug
title: "Pane2ExtractedData uses DEMO_FIELDS hardcoded mock data — not wired to backend"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T14:50:00+05:30
estimate: M
tags: [frontend, mock-data, bug, extracted-data]
---

## Problem

`Pane2ExtractedData` in
`frontend/components/workbench/Pane2ExtractedData.tsx` uses a
hardcoded `DEMO_FIELDS` array to populate the extracted data panel.
When `runStatus === 'running'`, it sets `DEMO_FIELDS` after a 1.5s
`setTimeout` to simulate extraction delay. No backend API is called
to fetch real extraction results.

## Evidence

`frontend/components/workbench/Pane2ExtractedData.tsx:28-74`:
```typescript
const DEMO_FIELDS: ExtractedField[] = [
  { id: 'f1', name: 'vendor_name', value: 'ACME Corporation Inc.', confidence: 0.98, ... },
  { id: 'f2', name: 'invoice_number', value: 'INV-2026-1084', confidence: 0.94, ... },
  { id: 'f3', name: 'invoice_date', value: '2026-08-01', confidence: 0.88, ... },
  { id: 'f4', name: 'tax_amount', value: 145.5, confidence: 0.72, ... },
  { id: 'f5', name: 'total_amount', value: 1595.5, confidence: 0.96, ... },
];
```

Lines 92-99:
```typescript
useEffect(() => {
    if (phase === 'extraction') {
      if (runStatus === 'running') {
        const timer = setTimeout(() => {
          setFields(DEMO_FIELDS);
          setJsonText(JSON.stringify(DEMO_FIELDS, null, 2));
        }, 1500);
        return () => clearTimeout(timer);
```

## Impact

Users see fabricated extraction results — fake vendor names, invoice
numbers, amounts, and confidence scores. This is misleading for
demos, testing, and production. The data has no connection to the
actual document or backend processing.

## Reproduction or reasoning

1. Open the workbench.
2. Upload a file and start a "run" (which is also mock — see BLK-139).
3. Pane 2 shows DEMO_FIELDS after 1.5 seconds.
4. Values are always the same regardless of the uploaded document.

## Proposed resolution

1. Remove `DEMO_FIELDS` entirely.
2. When `runStatus === 'running'`, connect to the SSE stream and
   populate fields from real `field_update` events.
3. When `runStatus === 'completed'`, fetch the run result from
   `GET /api/v1/runs/{runId}` and display real extracted fields.
4. Show loading/empty/error states instead of fake data.

## Acceptance criteria

- [ ] `DEMO_FIELDS` array removed
- [ ] No `setTimeout` to fake extraction delay
- [ ] Fields populated from real SSE events or API response
- [ ] Loading state shown while waiting for data
- [ ] Empty state shown when no fields are extracted
- [ ] Error state shown when API call fails

## Validation plan

- Start a real run and verify Pane 2 shows real extracted fields
- Verify field count and values match backend response
- Verify loading/empty/error states display correctly

## Related issues

BLK-139 (startDemoRun mock data — same workbench flow),
BLK-132 (loading/empty/error states),
BLK-137 (mock data removal — missed this component)
