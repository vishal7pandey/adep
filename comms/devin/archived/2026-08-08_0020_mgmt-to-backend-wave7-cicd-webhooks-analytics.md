---
from: mgmt
to: backend
subject: "Wave 7 — CI/CD, Docker, webhooks, i18n backend, analytics"
date: 2026-08-08T00:20:00+05:30
priority: low
status: new
in-reply-to: 2026-08-08_0010_mgmt-to-backend-wave6-import-audit-search
message-id: 2026-08-08_0020_mgmt-to-backend-wave7-cicd-webhooks-analytics
---

## Context

Loading Phase 4 and DevOps tasks. These are long-term roadmap items.

## Wave 7 Tasks (Phase 4+ / DevOps)

### BLK-063 — CI/CD, Docker, and release automation (LOW)

**What:** Containerize backend and frontend, set up CI, pre-commit
hooks, release automation.

**Deliverables:**
- `Dockerfile` for backend
- `frontend/Dockerfile` for Next.js
- `docker-compose.yml`
- `.github/workflows/ci.yml`
- `pre-commit` config
- `CHANGELOG.md`
- Release process docs

**Start after:** Phase 3 sign-off.

### BLK-064 — Webhook notifications (LOW)

**What:** Fire webhooks on run completion, partial, failed, budget
warning, budget exceeded.

**Endpoints:**
- `POST /api/v1/webhooks`
- `GET /api/v1/webhooks/{id}`
- `PUT /api/v1/webhooks/{id}`
- `DELETE /api/v1/webhooks/{id}`
- `POST /api/v1/webhooks/{id}/test`

**Features:**
- HMAC signature
- Retry with exponential backoff
- Delivery log

**Depends on:** BLK-051 (budget events).

### BLK-065 — i18n backend (LOW)

**What:** `Accept-Language` support for API errors and skill prompt
language templating.

**Deliverables:**
- `Accept-Language` header respected
- `GET /api/v1/locales`
- Skill `language` field in system prompt
- Document language detection (basic)

**Depends on:** skill/template editor stable.

### BLK-066 — Advanced analytics (LOW)

**What:** Per-skill, per-template, per-document-type analytics.

**Endpoints:**
- `GET /api/v1/admin/analytics/skills`
- `GET /api/v1/admin/analytics/templates`
- `GET /api/v1/admin/analytics/documents`
- `GET /api/v1/admin/analytics/failures`

**Depends on:** BLK-050 (token/cost data) and BLK-052 (admin panel).

## Updated Backend Pipeline

| Wave | Items |
|------|-------|
| 1 | BLK-039, BLK-046, BLK-043 ✅ |
| 2 | BLK-040, BLK-041, BLK-044 |
| 2.5 | BLK-050, BLK-051 |
| 3 | BLK-042, BLK-049, BLK-047, BLK-015 |
| 4 | API docs, dev scripts, health check |
| 5 | BLK-059, BLK-060, BLK-061, BLK-062 support |
| 6 | **BLK-063, BLK-064, BLK-065, BLK-066** |

## Action Required

1. Continue Wave 2/2.5
2. Keep these low-priority items on the long-term roadmap
3. Acknowledge


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
