---
id: BLK-097
type: bug
title: "Frontend: all API calls silently fall back to mock data on error — masks backend failures"
priority: high
status: backlog
phase: 3
owner: frontend
created: 2026-08-08T02:30:00+05:30
estimate: M
depends-on: []
tags: [frontend, bug, api, mock-data, stabilization]
---

## Bug

Every API function in `frontend/lib/api.ts` uses the same pattern:

```typescript
export async function fetchDefinitions(): Promise<AgentDefinition[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/definitions`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return MOCK_DEFINITIONS;  // ← silent fallback
  }
}
```

This applies to **all 13 API functions**: `fetchDefinitions`,
`fetchDefinition`, `createDefinition`, `fetchSkills`, `createSkill`,
`fetchTemplates`, `createTemplate`, `startExtractionRun`,
`compactRun`, `pauseRun`, `resumeRun`, `stopRun`, `rollbackRun`,
`fetchRecentRuns`, `deleteRun`, `renameRun`, `duplicateRun`.

## Impact

1. **Backend failures are invisible** — if the API is down, the
   frontend shows mock data and the user thinks everything works.
2. **Mock data leaks into the UI** — `MOCK_DEFINITIONS` has 2
   entries (`def-invoice-v1`, `def-receipt-v2`) that don't exist in
   the backend. Starting a run with `def-receipt-v2` will fail.
3. **`startExtractionRun` returns a fake running run** — the user
   sees "running" but nothing is happening on the backend.
4. **`pauseRun`/`resumeRun`/`stopRun` return fake success** — user
   clicks pause, gets "paused" confirmation, but nothing paused.
5. **`fetchRecentRuns` returns a mock `run-001`** — the sidebar
   shows a fake session that doesn't exist.

## Fix

### 1. Add error state to API functions

```typescript
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function fetchDefinitions(): Promise<AgentDefinition[]> {
  const res = await fetch(`${API_BASE_URL}/definitions`);
  if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`);
  return await res.json();
}
```

### 2. Remove mock data constants

Delete `MOCK_DEFINITIONS`, `MOCK_SKILLS`, `MOCK_TEMPLATES`.

### 3. Components handle errors explicitly

```typescript
const [error, setError] = useState<string | null>(null);

useEffect(() => {
  fetchDefinitions()
    .then(setDefinitions)
    .catch((e) => setError(e.message));
}, []);
```

Show error state in the UI: "Failed to load — check backend
connection."

### 4. For mutation endpoints (start run, pause, etc.)

Don't fake success. If the backend is unreachable, show an error
toast: "Backend unavailable — cannot start run."

## Acceptance Criteria

- [ ] No mock data constants in `api.ts`
- [ ] API functions throw on error instead of returning mock data
- [ ] Components show error states when API calls fail
- [ ] User sees "Backend unavailable" instead of fake data when API is down
- [ ] No fake `run-001` in the sidebar sessions list
