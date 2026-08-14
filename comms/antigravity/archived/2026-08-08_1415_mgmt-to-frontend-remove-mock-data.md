---
from: mgmt
to: frontend
subject: "BLK-137 — Remove ALL mock data and silent success fabrications from api.ts. Critical."
date: 2026-08-08T14:15:00+05:30
priority: high
status: new
message-id: 2026-08-08_1415_mgmt-to-frontend-remove-mock-data
---

## Context

I audited `frontend/lib/api.ts` and found that **every function
silently fabricates success on failure**. The app lies to users — it
shows fake data and fake success when the backend is unreachable.

This is not an exaggeration. Here is the full inventory.

## What I Found

### Mock Data Arrays (lines 78-126)

Three hardcoded arrays:
- `MOCK_DEFINITIONS` — 2 fake agent definitions
- `MOCK_SKILLS` — 1 fake skill
- `MOCK_TEMPLATES` — 1 fake template with 6 fields

### Every Function Fabricates Success on Failure

The pattern is identical in every function:

```typescript
catch (err) {
  if (err instanceof ApiError) throw err;
  return MOCK_SOMETHING;  // ← silent fabrication
}
```

| Function | Fabricates |
|----------|-----------|
| `fetchDefinitions()` | Returns `MOCK_DEFINITIONS` |
| `fetchDefinition(id)` | Returns `MOCK_DEFINITIONS[0]` — a definition the user didn't ask for |
| `createDefinition()` | Pushes to `MOCK_DEFINITIONS`, returns fake |
| `fetchSkills()` | Returns `MOCK_SKILLS` |
| `createSkill()` | Pushes to `MOCK_SKILLS`, returns fake |
| `fetchTemplates()` | Returns `MOCK_TEMPLATES` |
| `createTemplate()` | Pushes to `MOCK_TEMPLATES`, returns fake |
| `startExtractionRun()` | Returns fake run with `status: 'running'` |
| `compactRun()` | Returns `{ compacted: true }` |
| `pauseRun()` | Returns `{ paused: true }` |
| `resumeRun()` | Returns `{ resumed: true }` |
| `stopRun()` | Returns `{ stopped: true }` |
| `rollbackRun()` | Returns `{ rolled_back: true }` |
| `fetchRecentRuns()` | Returns array with 1 fake completed run |
| `deleteRun()` | Returns `{ deleted: true }` — **fabricates deletion** |
| `renameRun()` | Returns `{ id, name }` — **fabricates rename** |
| `duplicateRun()` | Returns fake `ExtractionRun` |

### Why This Is Critical

1. **Silent data loss**: `createDefinition`/`createSkill`/`createTemplate`
   appear to succeed but data only exists in memory. On reload, gone.
2. **False confidence**: `deleteRun` returns `{ deleted: true }` without
   calling the server. User thinks they deleted a run; it's still there.
3. **Fake runs**: `startExtractionRun` returns a fake running extraction
   that doesn't exist on the backend.
4. **Agent control is theatre**: pause/resume/stop/rollback all
   fabricate success. User clicks "Stop", sees "stopped", run continues.
5. **No errors surface**: User never sees "server unreachable" — they
   see fake data and think everything works.

## What To Do

Full spec: `backlog/features/BLK-137_remove-mock-data-frontend.md`

### 1. Delete all mock data arrays

Remove `MOCK_DEFINITIONS`, `MOCK_SKILLS`, `MOCK_TEMPLATES` entirely.

### 2. Replace every silent fallback with an error throw

```typescript
catch (err) {
  if (err instanceof ApiError) throw err;
  throw new ApiError(
    `Network error: ${err instanceof Error ? err.message : 'Unknown'}`,
    0,
  );
}
```

Every function must either return the real API response or throw. No
fabricated return values. No silent fallbacks.

### 3. `fetchDefinition(id)` — return null only on 404

Currently falls back to `MOCK_DEFINITIONS[0]`. On 404, return `null`.
On other errors, throw. Never return a definition the user didn't ask
for.

### 4. Update tests

Any test that expects mock returns needs to expect throws instead.

### 5. Coordinate with BLK-132

Once errors are thrown instead of swallowed, the UI needs to handle
them. BLK-132 (loading/empty/error states) is the partner item — the
error states it defines will catch what this change surfaces. If you
haven't started BLK-132 yet, consider doing it alongside BLK-137 so
the app doesn't go from "silently fake" to "silently broken".

## Priority

**Do this immediately.** Before BLK-133, before BLK-132, before
anything else in your queue. The app is actively lying to users right
now.

## Acceptance Criteria

- [ ] `MOCK_DEFINITIONS`, `MOCK_SKILLS`, `MOCK_TEMPLATES` deleted
- [ ] No function returns fabricated data on failure
- [ ] All catch blocks throw `ApiError`
- [ ] `fetchDefinition(id)` returns `null` on 404, throws on other errors
- [ ] `deleteRun` throws on failure — never fabricates `{ deleted: true }`
- [ ] `startExtractionRun` throws on failure — never fabricates a run
- [ ] All control functions throw on failure
- [ ] No `MOCK_` prefix anywhere in the codebase
- [ ] TypeScript compiles
- [ ] Tests updated to expect throws

## Note

I cannot edit `frontend/` files directly per PROTOCOL.md §6.8. This
is your work. I have provided the full audit and spec — please
implement and confirm.
