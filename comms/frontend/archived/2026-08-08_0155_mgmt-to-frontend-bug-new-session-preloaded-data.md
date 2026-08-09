---
from: mgmt
to: frontend
subject: "BUG: New session page shows pre-loaded data — all 3 panes have hardcoded demo state"
date: 2026-08-08T01:55:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0155_mgmt-to-frontend-bug-new-session-preloaded-data
---

## Bug Description

When the user clicks "New Session", the `WorkbenchContext.reset()` is
called and `phase` returns to `'chat'`. However, the page still shows
pre-loaded data from the previous session (or demo data). The new
session page should be **completely blank**.

## Root Cause

All three pane components have **hardcoded demo data** in their initial
`useState` calls. They do not sync their internal state with
`WorkbenchContext`. When `reset()` is called, the context resets but
the component-internal state keeps its old values.

### Pane1AgentConsole.tsx — Hardcoded initial state

```typescript
// Line 41: should be 'idle', not 'completed'
const [runState, setRunState] = useState<'idle' | 'running' | 'paused' | 'completed' | 'stopped'>('completed');

// Line 44: should be null
const [activeRunId, setActiveRunId] = useState<string | null>('run-demo-101');

// Line 45: should be 0
const [completedFieldsCount, setCompletedFieldsCount] = useState(5);

// Line 46: should be 0
const [totalFields, setTotalFields] = useState(6);

// Line 47: should be 0
const [runningTokens, setRunningTokens] = useState(8500);

// Line 48: should be 0
const [runningCost, setRunningCost] = useState(0.05);

// Line 52: should be null — this is the biggest offender
const [uploadedFileName, setUploadedFileName] = useState<string | null>('sample_invoice.pdf');
```

The component reads `useWorkbench()` (line 57) but **never uses `phase`
or `runStatus` from context** to drive its internal state. The `reset()`
function from context is destructured but there is no `useEffect` that
listens to `phase` changes to reset internal state.

### Pane2ExtractedData.tsx — Hardcoded mock fields

```typescript
// Line 23-78: 6 pre-filled mock fields
const MOCK_FIELDS: ExtractedField[] = [ ... ];

// Line 81: initialized with mock data, never cleared
const [fields, setFields] = useState<ExtractedField[]>(MOCK_FIELDS);
```

Does not use `useWorkbench` at all. Fields are always the 6 mock fields.
When a new session starts, the old fields remain.

### Pane3DocumentViewer.tsx — Hardcoded invoice content

```typescript
// Lines 82-126: hardcoded ACME Corporation invoice HTML
<h1>ACME Corporation Inc.</h1>
<p>INVOICE #INV-2026-1084</p>
```

Does not use `useWorkbench` at all. Always renders the same mock
invoice document regardless of what document was uploaded.

## Fix Instructions

### Fix 1: Pane1AgentConsole.tsx — Reset internal state on phase change

**A. Change all initial state to empty/idle values:**

```typescript
const [runState, setRunState] = useState<'idle' | 'running' | 'paused' | 'completed' | 'stopped'>('idle');
const [activeRunId, setActiveRunId] = useState<string | null>(null);
const [completedFieldsCount, setCompletedFieldsCount] = useState(0);
const [totalFields, setTotalFields] = useState(0);
const [runningTokens, setRunningTokens] = useState(0);
const [runningCost, setRunningCost] = useState(0);
const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
```

**B. Add useEffect to sync with WorkbenchContext:**

```typescript
const { phase, runStatus, documentFileName, runId, reset } = useWorkbench();

useEffect(() => {
  if (phase === 'chat') {
    // New session — clear everything
    setCycles([]);
    setRunState('idle');
    setActiveRunId(null);
    setCompletedFieldsCount(0);
    setTotalFields(0);
    setRunningTokens(0);
    setRunningCost(0);
    setUploadedFileName(null);
    setCollapsedCycles({});
  } else if (phase === 'document') {
    setUploadedFileName(documentFileName);
    setRunState('idle');
  } else if (phase === 'extraction') {
    setActiveRunId(runId);
    setRunState(runStatus === 'completed' ? 'completed' : 'running');
  }
}, [phase, runStatus, documentFileName, runId]);
```

**C. Show empty state when phase === 'chat':**

In the render, when `phase === 'chat'` and `uploadedFileName === null`:
- Show "Upload a document to begin" message in the trace area
- Hide the progress bar (0/0 fields)
- Disable "Start Run" button
- Show upload control prominently

**D. Wire file upload to WorkbenchContext:**

```typescript
const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
  if (e.target.files && e.target.files[0]) {
    const file = e.target.files[0];
    setUploadedFileName(file.name);
    setDocument(file.name);  // ← calls WorkbenchContext.setDocument
  }
};
```

**E. Wire Start Run to WorkbenchContext:**

```typescript
const handleStartRun = () => {
  if (!uploadedFileName) return;  // guard: no document
  startRun();  // ← calls WorkbenchContext.startRun
};
```

### Fix 2: Pane2ExtractedData.tsx — Clear fields on new session

**A. Initialize with empty array, not mock data:**

```typescript
const [fields, setFields] = useState<ExtractedField[]>([]);
```

**B. Use WorkbenchContext to drive display:**

```typescript
import { useWorkbench } from '@/context/WorkbenchContext';

// Inside component:
const { phase, runStatus } = useWorkbench();
```

**C. Show "in progress" state when extraction is running:**

When `phase === 'extraction'` and `runStatus === 'running'` and
`fields.length === 0`:

```tsx
<div className="flex-1 flex items-center justify-center">
  <div className="text-center space-y-3">
    <div className="w-12 h-12 mx-auto rounded-full border-3 border-[#0071CE] border-t-transparent animate-spin" />
    <p className="text-sm font-semibold text-[var(--primary-text)]">Extracting fields from document...</p>
    <p className="text-xs text-muted">Agent is analyzing the document and extracting structured data.</p>
  </div>
</div>
```

When `fields.length > 0` and `runStatus === 'running'`: show field cards
that have arrived + a "more fields coming..." placeholder at bottom.

When `runStatus === 'completed'`: show full grid (existing behavior).

When `phase !== 'extraction'`: this pane is not rendered (WorkbenchLayout
handles this), so no empty state needed here.

**D. Remove or keep MOCK_FIELDS:** Keep the constant for testing/demo
purposes, but do NOT use it as the initial state. Fields should come
from SSE events or API responses.

### Fix 3: Pane3DocumentViewer.tsx — Show empty state when no document

**A. Use WorkbenchContext:**

```typescript
import { useWorkbench } from '@/context/WorkbenchContext';

// Inside component:
const { phase, documentFileName, documentUrl } = useWorkbench();
```

**B. Show placeholder when no document:**

When `phase === 'chat'` (no document uploaded yet), this pane is not
rendered by WorkbenchLayout. But as a safety check:

```tsx
if (!documentFileName) {
  return (
    <div className="h-full flex items-center justify-center bg-[var(--pane-bg)]">
      <div className="text-center space-y-2 text-muted">
        <FileText className="w-12 h-12 mx-auto opacity-30" />
        <p className="text-sm">No document loaded</p>
      </div>
    </div>
  );
}
```

**C. Replace hardcoded invoice with dynamic document:**

The hardcoded ACME invoice (lines 82-126) must be replaced with actual
document rendering based on `documentUrl`. For v1, if the URL is a
mock/placeholder, show a "Document preview not available" message with
the filename. The actual PDF/image rendering will come with a later
backlog item (document pre-processing).

For now, replace the hardcoded content with:

```tsx
<div className="w-full h-full p-8 flex flex-col items-center justify-center text-gray-400">
  <FileText className="w-16 h-16 mb-3 opacity-40" />
  <p className="text-sm font-medium">{documentFileName}</p>
  <p className="text-xs mt-1">Document preview will appear here</p>
</div>
```

### Fix 4: WorkbenchContext.tsx — Fix setDocument default

From the previous code review (Issue 1):

```typescript
// Current (broken):
const setDocument = (fileName: string, url = 'sample_invoice.pdf') => {

// Fix:
const setDocument = (fileName: string, url: string | null = null) => {
```

## Summary

| Pane | Problem | Fix |
|------|---------|-----|
| Pane1 | 7 useState values initialized with demo data | Reset to idle/empty + useEffect sync with context |
| Pane2 | Fields initialized with 6 mock fields | Init to `[]` + show "in progress" state |
| Pane3 | Hardcoded ACME invoice HTML | Show placeholder + use documentFileName from context |
| Context | Mock default URL | Default to `null` |

## Acceptance Criteria

- [ ] New session shows completely blank Pane 1 (no trace, no progress, no tokens)
- [ ] "Upload a document to begin" message shown in chat phase
- [ ] "Start Run" disabled until document uploaded
- [ ] Uploading document clears the empty state and shows filename
- [ ] Pane 2 shows "in progress" spinner when extraction starts (no mock fields)
- [ ] Pane 3 shows document filename, not hardcoded ACME invoice
- [ ] Selecting "New Session" after a completed run resets all panes to blank
- [ ] No mock data visible on new session page

## Priority

**Fix this immediately** — it blocks the BLK-078 progressive layout
demo. The progressive layout is meaningless if the new session page
shows old data.


## Resolution

Processed and completed code review fixes and New Session blank state bugfixes. Updated WorkbenchContext.tsx (fixed default url to null), Sidebar.tsx (fixed completed session loading, subtitle text, and added click-outside menu listener), WorkbenchLayout.tsx (reordered extraction phase to Pane 1, Pane 3, Pane 2 per spec), Pane1AgentConsole.tsx (cleared preloaded state on phase=chat, added useEffect context sync), Pane2ExtractedData.tsx (initialized fields to [] and added extraction spinner), and Pane3DocumentViewer.tsx (read documentFileName from context).
