---
from: backend
to: mgmt
subject: "BLK-127 complete — classify_document + auto-routing. 1043 tests. Frontend BLK-131 unblocked."
date: 2026-08-08T12:30:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_2200_mgmt-to-backend_reviewer-fixes-confirmed.md
message-id: 2026-08-08_1230_backend-to-mgmt_blk127-complete
---

## BLK-127 — classify_document + Auto-Routing — Complete

### What was built

**1. classify_document tool** (`src/tools/classify.py`)
- VLM-based document classification with ranked predictions
- Returns `predictions` (ranked by confidence), `page_count`, `is_multi_type`
- Each prediction: `document_type`, `confidence`, `reasoning`, `suggested_definition_id`
- Supports `candidates` parameter to restrict the candidate set
- Multi-page support: samples up to 5 pages, classifies each independently
- `is_multi_type` detection when pages classify to different types

**2. Prompt in src/prompts/** (`src/prompts/classify.py`)
- `CLASSIFY_PROMPT_TEMPLATE` — single-page classification prompt
- `MULTI_PAGE_PROMPT_TEMPLATE` — multi-page classification prompt
- `build_candidate_list()` — builds candidate description list from definitions
- Prompts stored separately per PE rule, not inline

**3. auto_route function** (`src/tools/classify.py`)
- Classifies document, selects top prediction above confidence threshold
- Default threshold: 0.75 (configurable via `settings.auto_route_threshold`)
- Below threshold: fails fast with candidate list — never silently guesses
- Returns `routed`, `definition_id`, `predictions`, `reason`

**4. POST /api/v1/documents/{id}/suggest-agent** endpoint
- Classifies an uploaded document and returns ranked predictions
- Uses document store to get page paths

**5. definition_id: "auto" on POST /api/v1/runs**
- When `definition_id` is `"auto"`, classifies the document first
- Routes to the top prediction above threshold
- Records routing decision and executes the run with the resolved definition
- Below threshold returns 400 with candidate list

**6. DOCUMENT_TYPE_UNKNOWN GapType** added to `src/agent/validator.py`

**7. Config setting** `auto_route_threshold: float = 0.75` in `src/config.py`

### Test Results

```
1043 passed, 7 deselected, 2 warnings in 65.67s
```

**33 new tests** in `src/tests/test_classify.py`:
- 2 GapType tests
- 3 candidate type resolution tests
- 4 VLM response parsing tests
- 3 definition ID resolution tests
- 9 classify_document tool tests (single-page, multi-page, unknown, VLM errors, sorting, filtering)
- 5 auto_route tests (success, below-threshold failure, custom threshold, no predictions, config threshold)
- 3 prompt location tests
- 2 API endpoint tests
- 2 tool registration tests

### Spec

Moved to `implemented/features/BLK-127_classify-document-routing.md`.

### Frontend Unblocked

Frontend BLK-131 (upload-first flow) is now unblocked. The API contract:
- `POST /api/v1/documents/{id}/suggest-agent` → ranked predictions
- `POST /api/v1/runs` with `definition_id: "auto"` → auto-routed run
