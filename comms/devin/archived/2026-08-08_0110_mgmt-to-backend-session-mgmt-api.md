---
from: mgmt
to: backend
subject: "Session management API endpoints needed for BLK-077"
date: 2026-08-08T01:10:00+05:30
priority: high
status: new
message-id: 2026-08-08_0110_mgmt-to-backend-session-mgmt-api
---

## Context

The frontend sidebar session manager (BLK-077) needs several API
endpoints that do not currently exist. The frontend team will build
against these with mock fallbacks, but we need the real endpoints
implemented.

## Required Endpoints

### 1. `GET /api/v1/runs?limit={N}`

Returns a list of recent runs sorted by recency (newest first).

**Response:** `ExtractionRun[]` — same shape as existing run object:
```json
[
  {
    "id": "run-001",
    "definition_id": "def-invoice-v1",
    "document_url": "sample_invoice.pdf",
    "status": "completed",
    "current_cycle": 6,
    "total_fields": 6,
    "extracted_fields_count": 6,
    "fields": []
  }
]
```

Default limit: 20. Max: 100.

### 2. `DELETE /api/v1/runs/{run_id}`

Deletes a run and its associated data (trace, token usage, etc.).

**Response:**
```json
{ "deleted": true }
```

Return 404 if run does not exist.

### 3. `POST /api/v1/runs/{run_id}/duplicate`

Creates a new run with the same definition and document as the source
run. The new run starts in `idle` status with no extracted fields.

**Response:** `ExtractionRun` (the new run)

### 4. `PATCH /api/v1/runs/{run_id}`

Updates run metadata. Initially just supports renaming:

**Request body:**
```json
{ "name": "My Invoice Extraction" }
```

**Response:**
```json
{ "id": "run-001", "name": "My Invoice Extraction" }
```

### 5. `GET /api/v1/runs/{run_id}` (confirm existing)

Confirm this endpoint already works and returns:
- `extracted_fields_count` (correct count, not always 0)
- `total_fields` (from the template schema)
- `status` (current run status)
- `fields` (array of extracted field objects)

If any of these are missing or incorrect, fix them.

## Also Needed (reminder from previous comms)

- `field_update` SSE event after each successful field extraction
- `status_change` SSE event on every run status transition

These are critical for the progressive workbench (BLK-078) and the
Pane 2 "in progress" state.

## Priority

1. Confirm/fix `GET /runs/{id}` field counts and status
2. Implement `GET /runs?limit=N`
3. Implement `DELETE /runs/{id}`
4. Implement `PATCH /runs/{id}` (rename)
5. Implement `POST /runs/{id}/duplicate`
6. Confirm SSE events (`field_update`, `status_change`)

## Acceptance

- [ ] `GET /runs?limit=10` returns 10 most recent runs
- [ ] `DELETE /runs/{id}` removes run data from disk
- [ ] `PATCH /runs/{id}` persists name to run metadata
- [ ] `POST /runs/{id}/duplicate` creates new idle run
- [ ] `GET /runs/{id}` returns correct `extracted_fields_count`
- [ ] `field_update` SSE fires after each field extraction
- [ ] `status_change` SSE fires on every status transition

## Constraints

- Runs are file-based (`.adep/runs/{id}/`) — no database needed yet
- Run metadata (name) can be stored in `run_meta.json` alongside existing
  run files
- Deletion should remove the entire run directory


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
