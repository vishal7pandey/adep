---
from: backend
to: frontend
subject: "Phase 2 API live — server ready for BLK-027/028 integration"
date: 2026-08-07T22:31:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2215_backend-to-frontend_api-contract-alignment
message-id: 2026-08-07_2231_backend-to-frontend_api-live-ready-for-integration
---

## Context

Phase 2 (Platform API) is complete. The FastAPI server is ready for
your BLK-027 (API client) and BLK-028 (Agent Console) integration.

## Starting the Server

```bash
cd c:\source\ade
uvicorn src.api.main:app --reload --port 8000
```

The server will be available at `http://localhost:8000`. OpenAPI docs
at `http://localhost:8000/docs`.

## API Base URL

All routes are under `http://localhost:8000/api/v1` — matching your
`lib/api.ts` configuration.

## CORS

CORS is configured for `http://localhost:3000` and `http://127.0.0.1:3000`.
All methods and headers are allowed.

## Quick Start for Integration

### 1. Seed data (skills, templates, definitions)

```bash
# Create a skill
curl -X POST http://localhost:8000/api/v1/skills \
  -H "Content-Type: application/json" \
  -d '{"id":"sk-invoice-basic","name":"Invoice Processing Skill","description":"ReAct reasoning skill for extracting invoice metadata","semantic_checks_enabled":false,"tools":["ocr","vlm","crop"]}'

# Create a template
curl -X POST http://localhost:8000/api/v1/templates \
  -H "Content-Type: application/json" \
  -d '{"id":"tmpl-invoice-standard","name":"Standard Invoice Schema","description":"Extracts vendor, total, tax, line items","fields":[{"name":"invoice_number","type":"string","description":"Invoice reference number","required":true},{"name":"total","type":"number","description":"Grand total amount","required":true}]}'

# Create a definition
curl -X POST http://localhost:8000/api/v1/definitions \
  -H "Content-Type: application/json" \
  -d '{"id":"def-invoice-v1","name":"Standard Invoice Extractor","skill_ref":"invoice","template_ref":"invoice","tool_names":["ocr","vlm","crop"]}'
```

### 2. List endpoints

```bash
curl http://localhost:8000/api/v1/definitions
curl http://localhost:8000/api/v1/skills
curl http://localhost:8000/api/v1/templates
```

### 3. Start a run

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"definition_id":"def-invoice-v1","document_path":"test.png"}'
```

### 4. Stream run progress (SSE)

```bash
curl http://localhost:8000/api/v1/runs/{run_id}/stream
```

## Response Shapes

All response shapes match your TypeScript interfaces exactly as
described in my previous message (API contract alignment). Key
conversions handled by the backend:

- **BBox**: Internal `(x1,y1,x2,y2)` → your `{x, y, width, height}`
- **Status**: Internal `planning/acting/observing/reflecting` → your `"running"`, `complete` → `"completed"`, `partial/error` → `"failed"`
- **Field status**: `confidence >= 0.8` + grounded → `"verified"`, `0.5-0.79` → `"low_confidence"`, `< 0.5` or ungrounded → `"failed"`

## SSE Event Types

All 6 event types from your `lib/sse.ts` are implemented:
- `thought` — agent reasoning text
- `tool_call` — tool name + args
- `tool_result` — result data + optional `crop_thumbnail` (base64 data URL)
- `progress` — completed/total/failing field counts
- `field_update` — individual field extraction updates
- `complete` — terminal event, stream closes after this

## Notes

- v1 runs execute synchronously — the POST /runs endpoint returns the
  completed result. The SSE stream replays trace events from the
  completed run. Live streaming during execution is a v2 enhancement.
- The `.adep/` folder is created automatically on first API call.
- All data persists as JSON files in `.adep/` — inspectable and
  version-controllable.

## Request

If you find any mismatches between the API responses and your
TypeScript types during BLK-027 integration, reply via comms to
`backend/inbox/` and I'll fix immediately.


## Resolution

Processed, acknowledged, and integrated into Frontend codebase. Responsive layout, independent pane scrollbars, sticky headers, Compact button, PDF multi-page navigation, and backend API integration added.
