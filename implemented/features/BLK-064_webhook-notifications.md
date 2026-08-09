---
id: BLK-064
type: feature
title: "Webhook notifications — run completion and budget alerts"
priority: low
status: backlog
phase: 4
owner: unassigned
created: 2026-08-08T00:15:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-022, BLK-051]
tags: [backend, webhooks, notifications, integrations, alerting]
---

## Description

Allow users to configure webhooks that fire on run completion, partial
result, budget warning, or budget exceeded. Integrates ADEP with Slack,
Microsoft Teams, or custom endpoints.

## Webhook Events

| Event | Trigger |
|-------|---------|
| `run.completed` | Extraction finished successfully |
| `run.partial` | Extraction finished with unresolved gaps |
| `run.failed` | Extraction error |
| `budget.warning` | 80% of any budget level reached |
| `budget.exceeded` | 100% of any budget level reached |

## Payload Format

```json
{
  "event": "run.completed",
  "run_id": "...",
  "definition_id": "...",
  "document_id": "...",
  "status": "complete",
  "extracted_fields_count": 6,
  "total_fields": 6,
  "tokens": 8500,
  "cost_usd": 0.052,
  "timestamp": "2026-08-08T00:15:00Z"
}
```

## API

- `POST /api/v1/webhooks` — create webhook
- `GET /api/v1/webhooks` — list
- `PUT /api/v1/webhooks/{id}` — update
- `DELETE /api/v1/webhooks/{id}` — delete
- `POST /api/v1/webhooks/{id}/test` — send test payload

## UI

- Admin panel → "Webhooks" section
- Form: URL, secret (for HMAC signature), events to subscribe
- Test button
- Delivery log (last 10 attempts, status, response code)

## Security

- Optional HMAC signature in `X-ADE-Signature` header
- Payload signed with webhook secret
- Retry with exponential backoff on 5xx or network errors
- Max 3 retries

## Acceptance Criteria

- [ ] Webhook config model and CRUD endpoints
- [ ] Events emitted for 5 event types
- [ ] Payload delivered to external URL
- [ ] HMAC signature option
- [ ] Retry logic (3 attempts, exponential backoff)
- [ ] Delivery log in admin panel
- [ ] Unit tests for webhook dispatch
- [ ] Integration test: run completes → webhook received

## Constraints

- v1: no queue system, direct HTTP calls. Use queue in v2.
- Webhooks are optional per definition/global
- Secret stored in `.adep/webhooks/` (v1 file-based)

## Dependencies

- BLK-022 (runs API)
- BLK-051 (budget events)
- BLK-052 (admin panel for UI)
