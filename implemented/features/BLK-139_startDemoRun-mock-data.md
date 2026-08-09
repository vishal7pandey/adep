---
id: BLK-139
type: bug
title: "startDemoRun in Pane1AgentConsole is entirely fabricated mock data"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T14:45:00+05:30
estimate: M
tags: [frontend, mock-data, bug, agent-console]
---

## Problem

`startDemoRun` in `frontend/components/workbench/Pane1AgentConsole.tsx`
fabricates an entire extraction run client-side — fake cycles, fake tool
calls, fake tool results, fake token counts, fake costs, and a fake
run ID (`run-${Date.now()}`). No backend API is called. The user sees
a simulated extraction that looks real but has no connection to actual
processing.

## Evidence

`frontend/components/workbench/Pane1AgentConsole.tsx:144-243`:

```typescript
const startDemoRun = () => {
    if (!uploadedFileName) return;
    setCycles([]);
    setRunState('running');
    setCompletedFieldsCount(0);
    setNotification(null);
    setRunningTokens(1200);  // fake
    setRunningCost(0.01);    // fake
    const newRunId = `run-${Date.now()}`;  // fabricated ID
    setActiveRunId(newRunId);
    startRun(newRunId);

    const demoSteps: ConsoleTraceCycle[] = [
      {
        cycleNumber: 1,
        thought: { text: `Initializing extraction agent...` },
        toolCall: { tool: 'paddle_ocr', args: { page: 1, psm: 3 } },
        toolResult: { result: { text_blocks_found: 38, avg_confidence: 0.96 } },
        // ... all hardcoded
      },
      // ... more fake cycles
    ];

    demoSteps.forEach((step, index) => {
      setTimeout(() => {
        setCycles((prev) => [...prev, step]);
        setCompletedFieldsCount((index + 1) * 2);
        setRunningTokens((index + 1) * 2800);
        setRunningCost((index + 1) * 0.018);
        // ...
      }, (index + 1) * 1200);
    });
  };
```

Also line 85: `setUploadedFileName(documentFileName || 'sample_invoice.pdf')`
— hardcoded fallback filename.

## Impact

Users see a simulated extraction that appears successful but never
touches the backend. This is misleading for demos, testing, and
production. The fabricated run ID doesn't exist in the backend, so
pause/resume/stop calls will fail with 404. Token and cost displays
are fictional.

## Reproduction or reasoning

1. Open the frontend workbench.
2. Upload a file (or set a document).
3. Click "Start Run" — `startDemoRun` fires.
4. Observe fake cycles appearing with `setTimeout` delays.
5. Check backend — no run was created.

## Proposed resolution

Replace `startDemoRun` with a real `startExtractionRun` API call from
`lib/api.ts`. Connect to the SSE stream via `connectToRunStream` to
receive real trace events. Remove all hardcoded cycle data, fake token
counts, and fake costs. The run ID must come from the backend response,
not `Date.now()`.

## Acceptance criteria

- [ ] `startDemoRun` removed entirely
- [ ] Run start calls `startExtractionRun(definitionId, documentUrl)` from `lib/api.ts`
- [ ] Run ID comes from backend response, not fabricated
- [ ] SSE events drive cycle/field/progress updates
- [ ] No hardcoded tool names, results, or token counts
- [ ] `'sample_invoice.pdf'` fallback removed

## Validation plan

- Verify run start hits `POST /api/v1/runs`
- Verify SSE stream connects to real run ID
- Verify no `Date.now()` run ID generation
- Verify error states display when backend is unavailable

## Related issues

BLK-137 (mock data removal from api.ts — missed this component),
BLK-090 (SSE replay not live),
BLK-129 (async run execution)
