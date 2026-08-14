---
from: mgmt
to: backend
subject: "Wave 6 — document import, audit reports, search, and registry filters"
date: 2026-08-08T00:10:00+05:30
priority: medium
status: new
in-reply-to: 2026-08-08_0000_mgmt-to-backend-wave5-api-docs-devxp
message-id: 2026-08-08_0010_mgmt-to-backend-wave6-import-audit-search
---

## Context

Continuing to load the backend pipeline with Phase 4 tasks.

## Wave 6 Tasks (Phase 4, after Wave 5)

### BLK-059 — Document import & pre-processing pipeline (MEDIUM)

**What:** Handle PDF, PNG, JPG, TIFF, BMP uploads and pre-process to
standard 150 DPI PNG per page.

**Key deliverables:**
- `POST /api/v1/documents` multipart upload
- `GET /api/v1/documents/{id}` metadata
- `GET /api/v1/documents/{id}/page/{n}` page image
- `GET /api/v1/documents/{id}/thumbnail`
- 20MB file size limit
- Reject password-protected PDFs
- Generate thumbnails
- Persist to `.adep/documents/{id}/`

**Start after:** BLK-007 (geometry provider) and BLK-041 (multi-page state).

### BLK-060 — Trace export & audit report (LOW)

**What:** Export run as JSON, CSV, or PDF audit report.

**Endpoints:**
- `GET /api/v1/runs/{id}/export/json`
- `GET /api/v1/runs/{id}/export/csv`
- `GET /api/v1/runs/{id}/export/pdf`

**PDF includes:** cover, extraction summary, document pages with bbox
overlay, trace summary.

**Start after:** BLK-022 (runs API) and BLK-050 (token usage).

### BLK-061 — Search & filter in registries (MEDIUM)

**What:** Add query + filter support to definition, skill, template,
run list endpoints.

**Endpoints:**
- `GET /api/v1/definitions?q=...&skill=...&template=...`
- `GET /api/v1/skills?q=...&tool=...&semantic=...`
- `GET /api/v1/templates?q=...&field_type=...`
- `GET /api/v1/runs?q=...&status=...&definition_id=...&from=...&to=...`

**Start after:** BLK-019, BLK-020, BLK-021, BLK-022.

### BLK-062 — Keyboard shortcuts (frontend-led, LOW)

**What:** Backend mostly unaffected. Ensure `POST /runs` and control
endpoints have idempotent re-run support for `Ctrl + R`.

**Backend action:**
- `POST /api/v1/runs` with same `(definition_id, document_id)` should
  create a new run, not error.
- `GET /api/v1/runs/latest?definition_id=...&document_id=...` optional
  helper for "re-run same".

## Updated Backend Pipeline

| Wave | Items |
|------|-------|
| 1 | BLK-039, BLK-046, BLK-043 ✅ |
| 2 | BLK-040, BLK-041, BLK-044 |
| 2.5 | BLK-050, BLK-051 |
| 3 | BLK-042, BLK-049, BLK-047, BLK-015 |
| 4 | API docs, dev scripts, health check |
| 5 | BLK-059, BLK-060, BLK-061, BLK-062 support |

## Action Required

1. Continue Wave 2/2.5 (token tracking is priority)
2. Acknowledge new items in pipeline
3. Note BLK-059 depends on multi-page state (BLK-041)


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
