---
from: mgmt
to: backend
subject: "BLK-127 confirmed (1043 tests). Next: BLK-124 (tool result caching)."
date: 2026-08-08T22:20:00+05:30
priority: high
status: done
message-id: 2026-08-08_2220_mgmt-to-backend_blk127-confirmed
in-reply-to: 2026-08-08_1230_backend-to-mgmt_blk127-complete
---

## BLK-127 — Confirmed

Verified:
- `src/tools/classify.py` — `classify_document()` at line 144,
  `auto_route()` at line 270
- `src/prompts/classify.py` — prompt templates stored separately
- `src/tests/test_classify.py` — 33 new tests
- `auto_route_threshold: 0.75` in `config.py`
- `POST /documents/{id}/suggest-agent` endpoint
- `definition_id: "auto"` on `POST /runs`

1043 tests. 127 items completed. Frontend BLK-131 is now unblocked —
I've assigned it to them with your API contract.

---

## Next: BLK-124 — Tool Result Caching

**Priority:** Medium
**Estimate:** L
**Status:** Active

**Spec file:** `backlog/features/BLK-124_tool-result-caching.md`

Every run re-pays full OCR/VLM cost. Add a caching layer so identical
tool calls (same input hash) return cached results instead of
re-invoking providers.

### Key requirements
- Cache key based on tool name + input hash
- TTL-based expiry (configurable)
- Cache hits should be logged/traceable so we can measure savings
- Store cache on disk (simple JSON or SQLite) — no external dependency
- Clear cache API endpoint for debugging
- Tests for cache hit/miss/expiry

### After BLK-124

| # | ID      | Title                                      | Est |
|---|---------|--------------------------------------------|-----|
| 1 | BLK-128 | Integration tests + benchmarks             | L   |
| 2 | BLK-130 | Structured logging + OpenTelemetry         | M   |
| 3 | BLK-129 | Async run execution (XL contract change)   | XL  |
| 4 | BLK-123 | Rate limiting                              | M   |

BLK-129 still needs a contract proposal per PROTOCOL.md S7.

Report completion via comms to mgmt inbox. Include test count.

## Resolution

BLK-124 (tool result caching) completed. Built:
- `src/tools/cache.py` — ToolCache with content-addressed key (sha256 of cache_version + tool_name + image_bytes_hash + canonical_json(params) + provider), two-level cache (in-memory LRU + file store under `.adep/cache/`), TTL expiry, LRU size eviction
- `ToolSpec.cacheable` flag (default False) in `src/tools/base.py`
- `ToolRegistry.call()` wired to check/populate cache for cacheable tools
- Cacheable tools marked: `ocr`, `detect_layout`, `vlm`, `read_table`, `read_chart`, `crop`, `deskew`, `read_tag`
- Config: `cache_enabled` (default true), `cache_ttl_seconds` (30 days), `cache_max_size_bytes` (2GB), `cache_memory_entries` (256), `cache_version` ("v1")
- `GET /api/v1/admin/cache/stats` — hits, misses, evictions, entries, hit_rate
- `DELETE /api/v1/admin/cache` — purge all entries
- Cache disable-able for tests via `settings.cache_enabled = False`

26 new tests in `test_cache.py`. 1069 total tests, 0 failures. Spec moved to `implemented/features/`.
