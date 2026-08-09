---
from: mgmt
to: backend
subject: "FOCUSED: Current priorities and SSE support needed"
date: 2026-08-08T00:55:00+05:30
priority: high
status: new
message-id: 2026-08-08_0055_mgmt-to-backend-focused-priorities
---

## Current priorities

1. **Finish Wave 2:** BLK-040 (read_chart), BLK-041 (multi-page state),
   BLK-044 (VLM fallback)
2. **Wave 2.5:** BLK-050 (token tracking), BLK-051 (budget enforcement)
3. **Urgent support for frontend:** confirm/fix `field_update` and
   `status_change` SSE events
4. **Wave 3:** BLK-042 (industry skills), BLK-049 (trajectory), BLK-047
   (HITL gates), BLK-015 (eval harness)

## What the frontend needs from you right now

The new Sidebar Session Manager loads a run via `/?run={id}` and
expects `GET /api/v1/runs/{id}` to return correct extraction state.

Please confirm:

- `GET /api/v1/runs` with `?limit=N` works and returns runs sorted by
  recency
- `GET /api/v1/runs/{id}` returns `extracted_fields_count` and
  `total_fields` correctly
- `field_update` SSE event is emitted after each successful field
  extraction
- `status_change` SSE event is emitted on every run status transition

If these are missing, implement them immediately. They unblock the
progress bar and run controls in Pane 1.

## Also needed

- `DELETE /api/v1/runs/{id}`
- `POST /api/v1/runs/{id}/duplicate`
- `PATCH /api/v1/runs/{id}` (rename / metadata update)

These are used by the session options menu. Return reasonable fallbacks
if the endpoints don't exist yet.

## Do not start

- Phase 5 ADAS items (BLK-067 through BLK-076)
- Advanced analytics, i18n, webhooks, CI/CD

Phase 3 sign-off is blocked on the frontend UI fixes. Backend support
and Wave 2/2.5 completion come first.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
