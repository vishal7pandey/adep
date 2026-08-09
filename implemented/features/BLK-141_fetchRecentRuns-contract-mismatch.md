---
id: BLK-141
type: bug
title: "fetchRecentRuns expects array but backend returns paginated dict — contract mismatch"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T14:45:00+05:30
estimate: S
tags: [frontend, backend, bug, api, contract-mismatch]
---

## Problem

`fetchRecentRuns` in `frontend/lib/api.ts` is typed to return
`Promise<ExtractionRun[]>` but the backend `GET /runs` endpoint returns
a paginated dict `{items: [...], total: number, page: number, limit: number}`.
The frontend will receive an object, not an array, and any `.map()`
or array operations will fail at runtime.

## Evidence

Frontend (`frontend/lib/api.ts:261-268`):
```typescript
export async function fetchRecentRuns(limit: number = 20): Promise<ExtractionRun[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/runs?limit=${limit}`);
    if (!res.ok) throw new ApiError(...);
    return await res.json();  // returns {items, total, page, limit}
  } catch (err) {
    rethrowAsApiError(err);
  }
}
```

Backend (`src/api/routes/runs.py:158-208`):
```python
@router.get("/runs")
async def list_runs(...) -> dict[str, Any]:
    ...
    return {
        "items": runs[start:end],
        "total": len(runs),
        "page": page,
        "limit": limit,
    }
```

## Impact

Any component calling `fetchRecentRuns` and iterating over the result
with array methods (`.map`, `.filter`, `.find`, etc.) will crash at
runtime with `TypeError: res.json(...).map is not a function`. The
Sidebar's session list and any run history view are affected.

## Reproduction or reasoning

1. Start the backend with some runs in the store.
2. Call `fetchRecentRuns()` from the frontend.
3. The response is `{items: [...], total: N, page: 1, limit: 20}`.
4. Try to `.map()` over the result — crashes.

## Proposed resolution

Either:
- **Option A (frontend fix):** Update `fetchRecentRuns` to extract
  `.items` from the response: `const data = await res.json(); return data.items;`
- **Option B (backend fix):** Change `list_runs` to return a plain
  array (lose pagination metadata).

Option A is preferred — pagination metadata is useful for future
features.

## Acceptance criteria

- [ ] `fetchRecentRuns` returns `ExtractionRun[]` at runtime
- [ ] Paginated response is correctly unwrapped
- [ ] TypeScript types match runtime behavior

## Validation plan

- Call `fetchRecentRuns()` against a running backend with runs
- Verify the result is an array, not an object
- Verify `.map()` works on the result

## Related issues

BLK-098 (frontend create definition field mismatch — similar
contract mismatch pattern)
