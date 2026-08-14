---
id: BLK-273
type: feature
title: "Webhook delivery history, retry UI, and failure dashboard"
priority: low
status: backlog
phase: 5
owner: unassigned
created: 2026-08-09T10:50:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [webhooks, observability, ux, api]
---

## Description

Webhooks (BLK-064) support create/list/update/delete/test, but there is no delivery history or failure visibility. When a webhook delivery fails (network error, 5xx, timeout), the operator has no way to see:

- Which webhook failed
- When it failed
- What the error was
- Whether retries are still pending
- A way to manually re-dispatch a failed event

This is a real operational gap: webhooks are a core integration point (run completion, budget alerts), and silent delivery failures undermine trust in the platform.

## Feature Request

- Backend: persist webhook delivery attempts (event, webhook_id, status, error, attempts, timestamp)
- Backend: add `GET /api/v1/webhooks/{id}/deliveries` endpoint
- Backend: add `POST /api/v1/webhooks/{id}/deliveries/{delivery_id}/retry` endpoint
- Frontend: add a delivery history panel to the webhook management UI (if one exists) or a simple admin view
- Optionally: add a webhook failure count to the analytics dashboard

## Acceptance Criteria

- [ ] Delivery attempts are persisted to `.adep/webhooks/deliveries/`
- [ ] `GET /api/v1/webhooks/{id}/deliveries` returns paginated delivery history
- [ ] Manual retry endpoint re-dispatches a failed delivery
- [ ] Frontend shows delivery history with status badges and error details
- [ ] Tests cover persistence, listing, and retry

## Constraints

- Must not break existing webhook CRUD endpoints
- Delivery history should be bounded (e.g. keep last 100 per webhook) to avoid unbounded disk growth

## Dependencies

- None

## Notes

- Found during webhook module audit
- Related to BLK-064 (webhooks) and BLK-130 (observability)