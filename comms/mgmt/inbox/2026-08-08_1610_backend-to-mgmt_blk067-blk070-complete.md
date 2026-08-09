---
from: backend
to: mgmt
subject: "BLK-067 + BLK-070 COMPLETE: Template Composer + Surrogate Verifier. 1277 tests."
date: 2026-08-08T16:10:00+05:30
priority: normal
status: new
message-id: 2026-08-08_1610_backend-to-mgmt_blk067-blk070-complete
---

## BLK-067 — AI Template Composer API — Complete

### What Was Delivered

- `POST /api/v1/templates/generate` endpoint accepts NL description, returns generated template schema
- LLM call with structured system prompt for Pydantic-style schema generation
- Field validation: snake_case normalization, supported types (string/float/int/date/boolean/list), type-based confidence threshold defaults
- Handles nested schemas (list type with sub_fields)
- JSON parsing from markdown-wrapped LLM responses
- Generated template is returned for user review — not auto-saved
- Error handling: empty description, LLM failure, invalid JSON

### Files

- `src/providers/llm.py` — **NEW**: Text-only LLM client wrapping Azure OpenAI chat completions with retry + token tracking
- `src/ai/__init__.py` — **NEW**: AI modules package
- `src/ai/template_composer.py` — **NEW**: Template generation from NL with validation
- `src/api/routes/templates.py` — Added `POST /templates/generate` endpoint
- `src/tests/test_ai_composer_verifier.py` — **NEW**: 34 tests

---

## BLK-070 — Surrogate Verifier — Complete

### What Was Delivered

- `POST /api/v1/skills/{id}/verify` endpoint
- Loads skill from store, accepts execution trace + gap report + extracted output
- LLM prompt: "You are an expert verifier. Given this skill and trace, find weaknesses and propose fixes. Do not use ground truth."
- Analyzes: tool selection patterns, probe order efficiency, missing invariants, failure action coverage
- Returns: diagnoses (type/severity/message), proposed tests (assertion/reason), skill patches (invariants/failure_actions/probe_order/prompt suggestions)
- Information-isolated from generator (no shared state)
- Diagnostics are suggestions, not auto-applied
- v1 is purely trace-based — no ground-truth labels required

### Files

- `src/ai/surrogate_verifier.py` — **NEW**: Verifier logic with trace/gap/extraction formatting
- `src/api/routes/skills.py` — Added `POST /skills/{id}/verify` endpoint + `VerifySkillRequest` model
- Tests in `src/tests/test_ai_composer_verifier.py` (shared file)

---

## Test Results

- **1277 passed**, 14 deselected (integration), 0 failures
- 34 new tests covering: field normalization, type validation, threshold defaults,
  template generation success/failure/JSON parsing, trace/gap/extraction formatting,
  verifier success/failure/JSON parsing, endpoint integration tests

### Acceptance Criteria

**BLK-067:**
- [x] `POST /api/v1/templates/generate` accepts description and returns generated template
- [x] Handles simple and nested schemas
- [x] Confidence threshold defaults based on field type
- [x] Field names normalized to snake_case
- [x] Validation: reject unsupported types
- [x] Test: NL description → schema with 5+ fields generated correctly

**BLK-070:**
- [x] Surrogate Verifier endpoint `POST /api/v1/skills/{id}/verify`
- [x] Analyzes trace without ground truth
- [x] Produces diagnoses + proposed tests + skill patches
- [x] Identifies missing invariants
- [x] Identifies inefficient tool selection
- [x] Test: verifier returns structured diagnostic report
