---
id: BLK-093
type: bug
title: "Backend: start_run sends document_path but API expects document_url — field mismatch"
priority: high
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, frontend, bug, api-contract, stabilization]
---

## Bug

### Backend

`src/api/routes/runs.py` line 37:
```python
class StartRunRequest(BaseModel):
    document_path: str = Field(description="Path to the document to extract")
```

### Frontend

`frontend/lib/api.ts` line 203:
```typescript
body: JSON.stringify({ definition_id: definitionId, document_url: documentUrl }),
```

The frontend sends `document_url`, the backend expects `document_path`.
Pydantic drops the unknown field, `document_path` is never set, and
the run fails with a validation error or empty path.

## Fix

Align the field name. Use `document_path` everywhere (since the
backend actually needs a filesystem path, not a URL):

### Frontend fix:

```typescript
body: JSON.stringify({ definition_id: definitionId, document_path: documentUrl }),
```

### OR backend fix:

```python
class StartRunRequest(BaseModel):
    document_path: str = Field(
        default="",
        alias="document_url",  # accept both
        description="Path or URL to the document to extract",
    )
    model_config = {"populate_by_name": True}
```

## Acceptance Criteria

- [ ] Starting a run from the frontend sends the correct field name
- [ ] `execute_run` receives a non-empty `document_path`
- [ ] No validation errors when starting a run
