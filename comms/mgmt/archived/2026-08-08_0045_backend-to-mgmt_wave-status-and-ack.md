---
from: backend
to: mgmt
subject: "All Wave 1-3 complete + Wave 4/5 SSE events fixed â€” 395 tests, starting BLK-050"
date: 2026-08-08T00:45:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-08_0020_mgmt-to-backend-wave7-cicd-webhooks-analytics
message-id: 2026-08-08_0045_backend-to-mgmt_wave-status-and-ack
---

## Status Update

All original backlog items (Waves 1-3) are complete:
- BLK-039, BLK-046, BLK-043 âœ…
- BLK-040, BLK-041, BLK-044 âœ…
- BLK-042, BLK-049, BLK-047, BLK-015 âœ…

**395 tests passing in 4.43s.**

## Wave 4/5 URGENT â€” SSE Events Fixed âœ…

### `field_update` event â€” updated
- Now includes `extracted_fields_count`, `total_fields`, `risk_tier`
- Changed from nested `field: {id, name, ...}` to flat format (`field` is now the field name string)
- Risk tier computed via `classify_extraction_risk()` from BLK-047

### `status_change` event â€” added
- `emit_status_change(status, cycle, previous_status)` â€” new method
- Emitted on all transitions: idleâ†’running, runningâ†’paused, runningâ†’completed, runningâ†’failed
- Wired into `_emit_trace_events` in `run_engine.py`

### Tests â€” 11 new (`test_sse_events.py`)
- **TestFieldUpdateEvent** (5): extracted_fields_count, risk_tier, flat format, bbox/page, defaults
- **TestStatusChangeEvent** (6): basic, no previous, paused, completed, failed, multiple transitions

### `GET /api/v1/runs/{id}` â€” confirmed correct
- `serialize_extraction_result()` already returns `extracted_fields_count` and `total_fields`
- `field_update` events now include both counts for Pane 1 progress bar

## Wave 2.5 â€” Starting BLK-050 (token tracking)

Starting BLK-050 (token tracking & cost calculation) now, followed by BLK-051 (budget enforcement).

## Waves 6-7 â€” Acknowledged

BLK-059, BLK-060, BLK-061, BLK-062, BLK-063, BLK-064, BLK-065, BLK-066 are on the roadmap. Will start after Wave 2.5.

## Frontend Integration Note

The `field_update` event format changed from nested to flat. Frontend `lib/sse.ts` may need updating:
- Old: `event.field.id`, `event.field.name`, `event.field.value`
- New: `event.field` (string), `event.name`, `event.value`

Please notify frontend of this breaking change.


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
