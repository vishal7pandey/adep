---
from: mgmt
to: backend
subject: "Wave 5 — API contract alignment, docs, and dev-experience improvements"
date: 2026-08-08T00:00:00+05:30
priority: medium
status: new
in-reply-to: 2026-08-07_2358_mgmt-to-backend-wave4-support-frontend-needs
message-id: 2026-08-08_0000_mgmt-to-backend-wave5-api-docs-devxp
---

## Context

Frontend is focused on UI fixes. Backend should continue Wave 2/2.5.
These next 3 items prepare the backend for scale and better developer
experience.

## Wave 5 Tasks (Phase 3/4)

### 1. Confirm `field_update` + `status_change` SSE events (URGENT, Phase 3)

The frontend UI bugs may be partly caused by missing or inconsistent
backend events. Confirm these immediately:

**`field_update`:**
```json
{
  "type": "field_update",
  "field": "vendor_name",
  "value": "ACME Corporation",
  "confidence": 0.98,
  "status": "extracted",
  "bbox": {"x": 0.12, "y": 0.34, "width": 0.20, "height": 0.05},
  "page": 1,
  "extracted_fields_count": 5,
  "total_fields": 6
}
```

**`status_change`:**
```json
{"type": "status_change", "status": "running", "cycle": 1, "previous_status": "idle"}
```

- [ ] Verify both events are emitted
- [ ] Add tests if missing
- [ ] Update OpenAPI docs and `lib/sse.ts` contract

### 2. API Documentation & OpenAPI Spec (MEDIUM, Phase 3)

The FastAPI app already has auto-generated docs at `/docs`, but we need:

- [ ] Tag all endpoints by resource (`Definitions`, `Skills`, `Templates`, `Runs`, `Admin`)
- [ ] Add response model examples for all endpoints
- [ ] Add descriptions to all query parameters
- [ ] Add error response schemas (`HTTPError` model)
- [ ] Generate static OpenAPI JSON at `/api/v1/openapi.json`
- [ ] Add a `GET /` landing page that links to `/docs` and the GitHub repo
- [ ] Add `X-Request-ID` header support for tracing (optional, v1)

### 3. Developer Experience — Seed Data & Local Dev Scripts (MEDIUM, Phase 3)

New frontend developers and evaluators need a quick-start experience.

- [ ] `make seed` or `python -m scripts.seed` to populate:
  - 1 definition: Standard Invoice Extractor
  - 1 skill: Invoice Processing Skill
  - 1 template: Standard Invoice Schema
  - 1 sample invoice PDF
- [ ] `make dev` starts both backend and frontend
- [ ] `make test` runs backend + frontend tests
- [ ] `make reset` clears `.adep/` data
- [ ] Add `scripts/seed.py` with sample data
- [ ] Add `scripts/dev.py` to launch both servers
- [ ] Add a `CONTRIBUTING.md` with setup steps
- [ ] Ensure `.env.example` has all required keys with comments

### 4. Health Check & Observability (LOW, Phase 4)

- [ ] `GET /health` endpoint: checks provider connectivity (OCR, VLM)
- [ ] `GET /ready` endpoint: checks file store and config
- [ ] Log structured JSON in production mode (`ADE_LOG_LEVEL=INFO`)
- [ ] Add request logging middleware with path, status, duration
- [ ] Optional: OpenTelemetry traces (v2)

### 5. LLM Client Refactor for Token Usage (HIGH, Phase 4, part of BLK-050)

As prep for BLK-050:

- [ ] Refactor `llm_client.invoke()` to return an object:
  ```python
  {"content": "...", "usage": {"prompt_tokens": ..., "completion_tokens": ...}}
  ```
- [ ] Update `plan_node` and `compact_node` to use `response.content`
- [ ] Add `tiktoken` for token estimation fallback
- [ ] Add cost calculation helper

### 6. Test Coverage Enforcement (MEDIUM, Phase 4)

- [ ] `pytest --cov=src` with minimum 80% coverage
- [ ] Add `pytest-cov` to dev dependencies
- [ ] Add coverage step to CI (if CI exists) or pre-commit hook
- [ ] Document coverage command in README

## Updated Backend Pipeline

| Wave | Items | Status |
|------|-------|--------|
| 1 | BLK-039, BLK-046, BLK-043 | ✅ Done |
| 2 | BLK-040, BLK-041, BLK-044 | Working |
| 2.5 | **BLK-050, BLK-051** | Token/budget (high) |
| 3 | BLK-042, BLK-049, BLK-047, BLK-015 | Queued |
| 4 | BLK-048 (backend share), API docs, dev scripts | This message |
| 5 | Health/observability, test coverage | Later |

## Action Required

1. **Urgent:** confirm `field_update` and `status_change` events
2. Continue Wave 2 (BLK-040, BLK-041, BLK-044)
3. Implement LLM client refactor for BLK-050
4. API docs and seed scripts when time permits
5. Acknowledge by replying to `mgmt/inbox/`


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
