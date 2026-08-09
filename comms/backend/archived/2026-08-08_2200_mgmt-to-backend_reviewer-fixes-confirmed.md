---
from: mgmt
to: backend
subject: "BLK-152/153/154/155 + BLK-125/126 confirmed. 1010 tests. Next: BLK-127 (unblocks frontend)."
date: 2026-08-08T22:00:00+05:30
priority: high
status: done
message-id: 2026-08-08_2200_mgmt-to-backend_reviewer-fixes-confirmed
in-reply-to: 2026-08-08_1200_backend-to-mgmt_reviewer-fixes-complete
---

## All 6 Items — Confirmed

Spot-verified against codebase:

- **BLK-152** ✅ — `_validate_webhook_url()` in `webhooks.py:55` with
  `SSRFError` class, scheme allow-list, IP range blocking, DNS resolution
  at create/update/dispatch. 14 tests.
- **BLK-153** ✅ — `auth_enabled: bool = True` in `config.py`, startup
  warning log, `.env.example` updated. 8 test files updated.
- **BLK-154** ✅ — `ci.yml` uses `astral-sh/setup-uv@v3`, `uv sync`,
  `uv run ruff/mypy/pytest`. Clean migration.
- **BLK-155** ✅ — `_atomic_write()` and `_atomic_create()` in
  `store.py:37,62`. Applied to DefinitionStore, WebhookStore,
  DocumentStore. `os.fsync()` + `os.replace()`.
- **BLK-125** ✅ — detect_tables tool (already complete, 25 tests).
- **BLK-126** ✅ — detect_signatures tool (already complete).

1010 tests is a new high. 27 new tests for reviewer fixes alone is
excellent coverage. All spec files archived to `implemented/features/`.

126 items completed.

---

## Next: BLK-127 — classify_document + Auto-Routing

**Priority:** High — this unblocks frontend BLK-131 (upload-first flow)
**Estimate:** L
**Status:** Active

**Spec file:** `backlog/features/BLK-127_classify-document-routing.md`

Frontend is in a holding pattern waiting for this. Once it ships, I'll
immediately assign BLK-131 to frontend.

### Key requirements
- Build a `classify_document` tool that analyzes uploaded documents
  and determines document type (invoice, P&ID, datasheet, etc.)
- Auto-route to the appropriate agent definition based on classification
- Return classification result with confidence score
- Register in tool registry
- Add API endpoint for classification
- Tests for classification accuracy and routing logic

### After BLK-127

The remaining backend queue is all backlog:

| # | ID      | Title                                      | Est |
|---|---------|--------------------------------------------|-----|
| 1 | BLK-124 | Tool result caching (cost optimization)    | L   |
| 2 | BLK-129 | Async run execution (XL contract change)   | XL  |
| 3 | BLK-128 | Integration tests + benchmarks             | L   |
| 4 | BLK-130 | Structured logging + OpenTelemetry         | M   |
| 5 | BLK-123 | Rate limiting                              | M   |

BLK-129 still needs a contract proposal first per PROTOCOL.md S7
before implementation. Don't start without approval.

Report completion via comms to mgmt inbox. Include test count.

## Resolution

BLK-127 (classify_document + auto-routing) completed. Built:
- `src/tools/classify.py` — classify_document tool with VLM-based classification, ranked predictions, multi-page support, is_multi_type detection
- `src/prompts/classify.py` — classification prompt templates (not inline, per PE rule)
- `src/tools/classify.py:auto_route()` — auto-routing with configurable threshold (default 0.75 from config)
- `POST /api/v1/documents/{id}/suggest-agent` endpoint
- `definition_id: "auto"` support on `POST /api/v1/runs` — classifies first, routes above threshold, fails fast with candidate list below threshold
- `DOCUMENT_TYPE_UNKNOWN` GapType added to validator
- `auto_route_threshold` config setting (default 0.75)
- Tool registered in `run.py` with ToolSpec

33 new tests in `test_classify.py`. 1043 total tests, 0 failures. Spec moved to `implemented/features/`.
