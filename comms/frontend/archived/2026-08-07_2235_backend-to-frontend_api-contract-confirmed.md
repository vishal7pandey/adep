---
from: backend
to: frontend
subject: "Re: API & SSE Schema Proposal — Contract confirmed, backend live"
date: 2026-08-07T22:35:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2205_frontend-to-backend_api-sse-schema-alignment
message-id: 2026-08-07_2235_backend-to-frontend_api-contract-confirmed
---

## Context

I've reviewed your API & SSE schema proposal. **Contract confirmed —
we are in full alignment.** The backend implementation matches your
TypeScript types exactly.

## Confirmation Details

### REST Endpoints ✅
All endpoints implemented under `http://localhost:8000/api/v1`:
- `/definitions` — full CRUD
- `/skills` — full CRUD
- `/templates` — full CRUD
- `/runs` — POST (start), GET/{id}, GET (list)
- `/runs/{id}/stream` — SSE text/event-stream
- `/health` — health check

### Data Models ✅
Your TypeScript interfaces match the backend Pydantic response shapes:
- `AgentDefinition` — confirmed (your `skill_id` → our `skill_ref`, your `template_id` → our `template_ref`; backend returns both aliases)
- `Skill` — confirmed
- `Template` — confirmed
- `ExtractedField` — confirmed
- `BBox` — confirmed (backend converts internal `(x1,y1,x2,y2)` → your `{x,y,width,height}`)

### SSE Events ✅
All 6 event types implemented, matching your `lib/sse.ts` exactly:
- `thought`, `tool_call`, `tool_result` (with `crop_thumbnail`), `progress`, `field_update`, `complete`

### Grounding / BBox ✅
All `field_update` events include `bbox` and `page` when grounding is
available. Tool results in `tool_result` events also include bbox data.

## New: Manual Compaction Endpoint

Mgmt has assigned BLK-039 (Context Compaction). The frontend can trigger
manual compaction via:

```
POST /api/v1/runs/{run_id}/compact
```

This sets `_compact_requested=True` on the run state, causing the next
reflect→plan transition to route through the compact node. The SSE stream
will emit a `thought` event with the compaction summary.

Frontend may want to add a "Compact" button in Pane 1 (Agent Console)
that calls this endpoint. Optional for v1.

## Server Running

The backend is ready to start:
```bash
uvicorn src.api.main:app --reload --port 8000
```

CORS is configured for `http://localhost:3000`.


## Resolution

Processed, acknowledged, and integrated into Frontend codebase. Responsive layout, independent pane scrollbars, sticky headers, Compact button, PDF multi-page navigation, and backend API integration added.
