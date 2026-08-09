---
id: BLK-157
title: Silent error swallowing — 4 components catch errors without error states
status: open
priority: high
estimate: M
assigned_to: frontend
created: 2026-08-08T22:25:00+05:30
tags: [error-handling, bug, frontend, ux]
---

## Problem

4 components silently swallow API errors with `.catch(() => ...)` and
show empty/blank UI instead of error messages. Users see blank pages
with no indication of what went wrong.

## Evidence

### 1. `Sidebar.tsx:44`
```typescript
fetchRecentRuns(10).then(setSessions).catch(() => setSessions([]));
```
Sessions list silently empties on error. No error indicator.

### 2. `Pane1AgentConsole.tsx:84`
```typescript
fetchDefinitions().then((defs) => {
  setDefinitions(defs);
  if (defs.length > 0) setSelectedDefId(defs[0].id);
}).catch(() => {
  setDefinitions([]);
});
```
Agent dropdown silently empties. User can't start a run but gets no
error message.

### 3. `Pane2ExtractedData.tsx:322`
```typescript
if (runId) fetchRun(runId).then((r) => r.fields && setFields(r.fields)).catch(() => {});
```
Worst case — completely empty catch. Fields silently disappear on
error with zero feedback.

### 4. `RunComparisonView.tsx:31,36,42`
```typescript
}).catch(() => setRuns([]));       // line 31
fetchRun(runAId).then(setRunA).catch(() => setRunA(null));  // line 36
fetchRun(runBId).then(setRunB).catch(() => setRunB(null));  // line 42
```
Comparison view silently shows empty state on any error.

### 5. `definitions/page.tsx:31,35` — Partial error state
```typescript
}).catch(() => setSkills([]));     // line 31 — silent
}).catch(() => setTemplates([]));  // line 35 — silent
```
Definitions page has error state for `fetchDefinitions()` but silently
swallows errors for `fetchSkills()` and `fetchTemplates()`. The wizard
will show empty dropdowns with no explanation.

## Resolution

Each component should:
1. Add `const [error, setError] = useState<string | null>(null);`
2. In catch blocks: `setError(e instanceof ApiError ? ... : String(e))`
3. Render an error banner with context-appropriate message
4. Include hints for common error codes:
   - **401**: "Authentication is enabled. Set an API key via the API Key Management page."
   - **Network error (status 0)**: "Backend server is not running. Start it with: `uv run uvicorn src.api.app:app --reload --port 8000`"

Follow the same error banner pattern already implemented in
`definitions/page.tsx`, `skills/page.tsx`, and `templates/page.tsx`.

## Tests

- Each component renders error banner when API fails
- Error banner shows correct hint for 401 vs network error
- Error state clears on successful retry
