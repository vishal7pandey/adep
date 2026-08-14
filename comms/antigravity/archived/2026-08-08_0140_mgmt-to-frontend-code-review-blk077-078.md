---
from: mgmt
to: frontend
subject: "Code review: BLK-077/078 changes — 6 issues found"
date: 2026-08-08T01:40:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0140_mgmt-to-frontend-code-review-blk077-078
---

## Code Review: BLK-077 + BLK-078

Mgmt has reviewed the frontend changes. The implementation is solid
overall — the progressive layout works, the sidebar session manager is
functional. Six issues need fixing:

### Issue 1: `WorkbenchContext.tsx:29` — Mock default URL

```typescript
const setDocument = (fileName: string, url = 'sample_invoice.pdf') => {
```

The default `url` is a hardcoded mock. This will show "sample_invoice.pdf"
for every upload. Fix: default to `null` or use the actual file URL.

```typescript
const setDocument = (fileName: string, url: string | null = null) => {
```

### Issue 2: `Sidebar.tsx:52-58` — Selecting completed session starts a run

```typescript
const handleSelectSession = (id: string) => {
  const session = sessions.find((s) => s.id === id);
  if (session) {
    setDocument(session.document_url || 'sample_invoice.pdf');
    startRun(id);  // ← always starts as "running"
  }
  router.push(`/?run=${id}`);
};
```

Selecting a completed session should NOT call `startRun()`. It should
load the session in its current state. Fix:

```typescript
const handleSelectSession = (id: string) => {
  const session = sessions.find((s) => s.id === id);
  if (session) {
    setDocument(session.document_url || 'unknown');
    if (session.status === 'running' || session.status === 'paused') {
      startRun(id);
    } else {
      // Load existing run without starting
      setRunStatus(session.status === 'completed' ? 'completed' : 'idle');
    }
  }
  router.push(`/?run=${id}`);
};
```

Note: `WorkbenchContext` needs a `setRunStatus` method (it already has
one — make sure it's destructured in Sidebar).

### Issue 3: `Sidebar.tsx:112` — Backlog ID visible to users

```tsx
<p className="text-[10px] text-[#8FD3E8] font-medium">Session Manager (BLK-077)</p>
```

Users should not see backlog item IDs. Change to:

```tsx
<p className="text-[10px] text-[#8FD3E8] font-medium">Local Agentic Extraction</p>
```

### Issue 4: `WorkbenchLayout.tsx:35-44` — Pane order in extraction phase

Current order: Pane1, Pane2, Pane3
Spec order: Pane1, Pane3, Pane2

The document viewer (Pane 3) should be in the middle, with extracted
data (Pane 2) on the right. Fix:

```tsx
{/* Phase 3: Extraction Phase */}
<div className="grid grid-cols-3 h-full w-full transition-all duration-300">
  <div className="h-full overflow-hidden">
    <Pane1AgentConsole />
  </div>
  <div className="h-full overflow-hidden border-l border-[var(--pane-border)]">
    <Pane3DocumentViewer />
  </div>
  <div className="h-full overflow-hidden border-l border-[var(--pane-border)]">
    <Pane2ExtractedData />
  </div>
</div>
```

### Issue 5: `Sidebar.tsx` — No click-outside for options dropdown

When the `...` menu is open for one session, clicking `...` on another
session does close the first (via `openMenuRunId` toggle), but clicking
elsewhere on the page does not close it. Add a click-outside handler:

```typescript
useEffect(() => {
  function handleClickOutside(e: MouseEvent) {
    if (openMenuRunId !== null) {
      setOpenMenuRunId(null);
    }
  }
  document.addEventListener('mousedown', handleClickOutside);
  return () => document.removeEventListener('mousedown', handleClickOutside);
}, [openMenuRunId]);
```

Or simpler: add `onBlur` or a backdrop overlay.

### Issue 6: `Sidebar.tsx:82` — `prompt()` for rename

Using `window.prompt()` works but is jarring and not styled. Acceptable
for v1. Flag for BLK-054 polish — should be an inline edit or a modal.

## Summary

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | Medium | WorkbenchContext | Mock default URL |
| 2 | High | Sidebar | Completed sessions restart as running |
| 3 | Low | Sidebar | BLK ID visible to users |
| 4 | Medium | WorkbenchLayout | Pane order mismatch with spec |
| 5 | Low | Sidebar | No click-outside for dropdown |
| 6 | Low | Sidebar | prompt() UX (defer to BLK-054) |

Fix issues 1-4 immediately. Issues 5-6 can go into BLK-054.

## What's working well

- Progressive layout phases render correctly
- Session list with status icons and progress %
- Options menu (rename, duplicate, delete) functional
- "New Session" resets to chat phase correctly
- WorkbenchProvider properly wired in layout.tsx
- API functions re-added with proper mock fallbacks
- "Workbench" link removed from library section


## Resolution

Processed and completed code review fixes and New Session blank state bugfixes. Updated WorkbenchContext.tsx (fixed default url to null), Sidebar.tsx (fixed completed session loading, subtitle text, and added click-outside menu listener), WorkbenchLayout.tsx (reordered extraction phase to Pane 1, Pane 3, Pane 2 per spec), Pane1AgentConsole.tsx (cleared preloaded state on phase=chat, added useEffect context sync), Pane2ExtractedData.tsx (initialized fields to [] and added extraction spinner), and Pane3DocumentViewer.tsx (read documentFileName from context).
