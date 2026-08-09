---
id: BLK-137
type: bug
title: "Remove all mock data and silent success fabrications from frontend API client"
priority: high
status: done
completed: 2026-08-08T10:15:00+05:30
phase: 4
owner: frontend
created: 2026-08-08T14:10:00+05:30
estimate: M
depends-on: []
tags: [frontend, bug, mock-data, production-readiness, critical]
---

## Problem

`frontend/lib/api.ts` contains three mock data arrays and **every
single function silently fabricates success on failure**. The pattern
is uniform:

```typescript
try {
  const res = await fetch(`${API_BASE_URL}/...`);
  if (!res.ok) throw new ApiError(...);
  return await res.json();
} catch (err) {
  if (err instanceof ApiError) throw err;
  return MOCK_SOMETHING;  // ← silent fabrication
}
```

This means any network failure, any backend downtime, any DNS
resolution issue — the user sees fake data and believes it's real.

### Mock Data Arrays (lines 78-126)

- `MOCK_DEFINITIONS` — 2 fake agent definitions
- `MOCK_SKILLS` — 1 fake skill
- `MOCK_TEMPLATES` — 1 fake template with 6 fields

### Silent Fabrications by Function

| Function | What it fabricates on failure |
|----------|-------------------------------|
| `fetchDefinitions()` | Returns `MOCK_DEFINITIONS` |
| `fetchDefinition(id)` | Returns `MOCK_DEFINITIONS[0]` |
| `createDefinition(data)` | Pushes to `MOCK_DEFINITIONS`, returns fake |
| `fetchSkills()` | Returns `MOCK_SKILLS` |
| `createSkill(data)` | Pushes to `MOCK_SKILLS`, returns fake |
| `fetchTemplates()` | Returns `MOCK_TEMPLATES` |
| `createTemplate(data)` | Pushes to `MOCK_TEMPLATES`, returns fake |
| `startExtractionRun()` | Returns fake `ExtractionRun` with `status: 'running'` |
| `compactRun()` | Returns `{ status: 'compact_requested', compacted: true }` |
| `pauseRun()` | Returns `{ paused: true, cycle: 2, ... }` |
| `resumeRun()` | Returns `{ resumed: true, cycle: 2, ... }` |
| `stopRun()` | Returns `{ stopped: true, cycle: 2, partial_result: [] }` |
| `rollbackRun()` | Returns `{ rolled_back: true, ... }` |
| `fetchRecentRuns()` | Returns array with 1 fake completed run |
| `deleteRun()` | Returns `{ deleted: true }` — **fabricates deletion success** |
| `renameRun()` | Returns `{ id: runId, name: newName }` — **fabricates rename** |
| `duplicateRun()` | Returns fake `ExtractionRun` |

### Why This Is Critical

1. **Silent data loss**: `createDefinition`, `createSkill`,
   `createTemplate` appear to succeed but the data only exists in
   memory. On page reload it's gone.
2. **False confidence**: `deleteRun` returns `{ deleted: true }`
   without ever calling the server. The user thinks they deleted a
   run; it's still there.
3. **Fake runs**: `startExtractionRun` returns a fake run with
   `status: 'running'` — the UI shows a running extraction that
   doesn't exist.
4. **Agent control is theatre**: `pauseRun`, `resumeRun`, `stopRun`,
   `rollbackRun` all fabricate success. The user clicks "Stop",
   sees "stopped", and the run keeps going on the backend.
5. **No error surfaces**: The user never sees "server unreachable" or
   "network error" — they see fake data and think everything works.

## Fix

### 1. Delete all mock data arrays

Remove `MOCK_DEFINITIONS`, `MOCK_SKILLS`, `MOCK_TEMPLATES` and their
type declarations entirely.

### 2. Remove every silent fallback

Every function must propagate errors. The catch block should either:
- Re-throw `ApiError` (already done)
- **Throw a new `ApiError` for network failures** instead of returning
  mock data

```typescript
} catch (err) {
  if (err instanceof ApiError) throw err;
  throw new ApiError(
    `Network error: ${err instanceof Error ? err.message : 'Unknown'}`,
    0,
  );
}
```

### 3. No fabricated return values

Every function must either:
- Return the real API response, or
- Throw an error

No function may return a fabricated object on failure.

### 4. Error surfacing in the UI

The UI components that call these functions must handle errors and
display them to the user (loading/empty/error states — BLK-132). This
is a separate item; this one is purely about the API client.

### 5. `fetchDefinition(id)` must return null only on 404

Currently falls back to `MOCK_DEFINITIONS[0]` — a real definition the
user didn't ask for. On 404, return `null`. On other errors, throw.

## Acceptance Criteria

- [ ] `MOCK_DEFINITIONS`, `MOCK_SKILLS`, `MOCK_TEMPLATES` deleted
- [ ] No function returns fabricated data on failure
- [ ] All catch blocks throw `ApiError` (re-throw existing or wrap network errors)
- [ ] `fetchDefinition(id)` returns `null` on 404, throws on other errors
- [ ] `deleteRun` throws on failure — never fabricates `{ deleted: true }`
- [ ] `startExtractionRun` throws on failure — never fabricates a run
- [ ] `pauseRun`/`resumeRun`/`stopRun`/`rollbackRun` throw on failure
- [ ] `createDefinition`/`createSkill`/`createTemplate` throw on failure
- [ ] No `MOCK_` prefix anywhere in the codebase
- [ ] TypeScript compiles with no errors
- [ ] All existing frontend tests updated to expect throws instead of mock returns
- [ ] No mock data imports or references remain

## Notes

This is a prerequisite for production readiness. The app currently
lies to users — it shows fake data and fake success when the backend
is unreachable. Every silent fabrication is a potential data loss
event or a false confidence event.

Coordinate with BLK-132 (loading/empty/error states) — the UI needs
to handle the errors that this change will now surface.
