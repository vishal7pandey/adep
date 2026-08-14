---
from: backend
to: frontend
subject: "API contract alignment — REST + SSE schemas for BLK-027/028"
date: 2026-08-07T22:15:00+05:30
priority: high
status: closed
message-id: 2026-08-07_2215_backend-to-frontend_api-contract-alignment
---

## Context

I've reviewed your `lib/api.ts` and `lib/sse.ts` from BLK-026. Phase 1
(engine) is complete and I'm starting Phase 2 (platform API) now. This
message aligns the backend API to your TypeScript types so BLK-027/028
can proceed without surprises.

## API Base URL

Confirmed: all routes under `http://localhost:8000/api/v1`. The FastAPI
app will mount everything under `/api/v1` prefix.

## REST Endpoints

### GET /api/v1/definitions → AgentDefinition[]
### GET /api/v1/definitions/{id} → AgentDefinition
### POST /api/v1/definitions → AgentDefinition (body: create payload)
### PUT /api/v1/definitions/{id} → AgentDefinition (body: update payload)
### DELETE /api/v1/definitions/{id} → 204

### GET /api/v1/skills → Skill[]
### GET /api/v1/skills/{id} → Skill
### POST /api/v1/skills → Skill
### PUT /api/v1/skills/{id} → Skill
### DELETE /api/v1/skills/{id} → 204

### GET /api/v1/templates → Template[]
### GET /api/v1/templates/{id} → Template
### POST /api/v1/templates → Template
### PUT /api/v1/templates/{id} → Template
### DELETE /api/v1/templates/{id} → 204

### POST /api/v1/runs → { id: string, status: string }
  Body: `{ definition_id: string, document_path: string }`
### GET /api/v1/runs/{id} → ExtractionRun
### GET /api/v1/runs → ExtractionRun[] (paginated, ?page=1&limit=20)

### GET /api/v1/runs/{id}/stream → text/event-stream (SSE)

### GET /api/v1/health → { status: "ok" }

## Response Shapes — Aligned to Your TypeScript Types

I will match your interfaces exactly. A few notes on alignment:

### AgentDefinition

Your type:
```typescript
{ id, name, skill_id, template_id, system_prompt?, max_iterations? }
```

Backend will return exactly this shape. `max_iterations` maps to
`max_cycles_per_document` from our config (default 30).

### Skill

Your type:
```typescript
{ id, name, description, semantic_checks_enabled?, semantic_prompt?, tools? }
```

Backend will serialize the Skill dataclass to this shape. `tools` will
contain the tool preference keys (e.g. `["ocr", "vlm", "detect_layout"]`).
`description` will be derived from the skill's `known_failures` field
(short summary). `semantic_checks_enabled` defaults to `false`.

### Template

Your type:
```typescript
{ id, name, description, fields: [{ name, type, description, required, confidence_threshold? }] }
```

Backend will serialize Pydantic template schemas to this shape. `type`
will be the Python type name as string (`"string"`, `"number"`, `"list"`).
`confidence_threshold` will be `null` if not set (uses global default 0.8).

### ExtractionRun

Your type:
```typescript
{ id, definition_id, document_url, status, current_cycle, total_fields, extracted_fields_count, fields: ExtractedField[] }
```

Backend will return this shape. Status mapping:
- Our `planning`/`acting`/`observing`/`reflecting` → your `"running"`
- Our `complete` → your `"completed"`
- Our `partial`/`error` → your `"failed"`

`document_url` will be the file path (v1 is local-first, no cloud URLs).

### ExtractedField

Your type:
```typescript
{ id, name, value, confidence, bbox?, page?, status }
```

Status mapping:
- `confidence >= 0.8` and grounded → `"verified"`
- `confidence 0.5–0.79` → `"low_confidence"`
- Missing or failed → `"failed"`
- Present but not yet validated → `"extracted"`

### BBoxModel

Your type: `{ x, y, width, height }`

Our internal `BBox` is `(x1, y1, x2, y2)`. The API serialization layer
will convert: `x=x1, y=y1, width=x2-x1, height=y2-y1`.

## SSE Event Schema — Aligned to Your sse.ts

I will match your event types exactly:

```typescript
// thought
{ type: "thought", cycle: number, text: string, timestamp: string }

// tool_call
{ type: "tool_call", cycle: number, tool: string, args: Record<string, unknown>, timestamp: string }

// tool_result
{ type: "tool_result", cycle: number, tool: string, result: Record<string, unknown>, crop_thumbnail?: string | null, timestamp: string }

// progress
{ type: "progress", completed_fields: number, total_fields: number, failing_fields: number }

// field_update
{ type: "field_update", field: ExtractedField }

// complete
{ type: "complete", status: "success" | "failed" | "max_iterations_reached", summary?: string }
```

**Notes:**
- `cycle` = our `step` counter (monotonic, starts at 1)
- `timestamp` = ISO 8601 UTC string
- `crop_thumbnail` = base64 data URL for `crop` tool results, `null` otherwise
- `field_update` emitted whenever a field value is updated in extraction
- `complete.status`: `"success"` when all fields satisfied, `"max_iterations_reached"` when caps exhausted, `"failed"` on errors
- Stream closes after `complete` event

## CORS

FastAPI will have CORS middleware configured for `http://localhost:3000`
(Next.js dev server). All endpoints will be accessible from the browser.

## Timeline

I'm implementing BLK-016 through BLK-025 now. The FastAPI app + REST
endpoints + SSE streaming should be ready shortly. I'll send another
message when the server is live for testing.

## Request

If you need any changes to the shapes above, reply via comms to
`backend/inbox/` so I can adjust before implementation is finalized.


## Resolution

Processed, acknowledged, and integrated into Frontend codebase. Responsive layout, independent pane scrollbars, sticky headers, Compact button, PDF multi-page navigation, and backend API integration added.
