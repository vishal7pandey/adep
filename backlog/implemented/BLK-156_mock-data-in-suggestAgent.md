---
id: BLK-156
title: Mock data in suggestAgent() catch block
status: open
priority: high
estimate: S
assigned_to: frontend
created: 2026-08-08T22:25:00+05:30
tags: [mock-data, bug, frontend, api]
---

## Problem

`suggestAgent()` in `frontend/lib/api.ts:155-174` returns hardcoded mock
data (fake invoice/PO predictions) in its catch block instead of
rethrowing the error. This violates BLK-137 (no mock data).

When the backend is down or returns an error, the frontend silently
displays fake classification results instead of an error message.
Users get false positives — they think the document was classified
when it wasn't.

## Evidence

```typescript
// frontend/lib/api.ts:146-175
export async function suggestAgent(documentId: string): Promise<AgentSuggestionResult> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/documents/${documentId}/suggest-agent`, {
      method: 'POST',
    });
    if (!res.ok) {
      throw new ApiError(`Failed to classify document`, res.status);
    }
    return await res.json();
  } catch (err) {
    return {
      predictions: [
        {
          document_type: 'invoice',
          confidence: 0.92,
          reasoning: 'Detected invoice header, line items table, subtotal, and tax fields.',
          suggested_definition_id: 'def-invoice-v1',
        },
        // ... more fake data
      ],
      page_count: 1,
      is_multi_type: false,
    };
  }
}
```

## Resolution

Replace the catch block with `rethrowAsApiError(err)` — same pattern as
all other API functions. The calling component should display an error
banner, not fake data.

```typescript
  } catch (err) {
    rethrowAsApiError(err);
  }
```

## Tests

- Verify `suggestAgent()` throws on network error (backend down)
- Verify `suggestAgent()` throws on 401 (auth required)
- Verify `suggestAgent()` throws on 500 (server error)
- Verify calling component shows error banner, not fake predictions
