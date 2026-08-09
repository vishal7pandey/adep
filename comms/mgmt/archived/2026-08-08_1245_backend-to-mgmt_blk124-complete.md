---
from: backend
to: mgmt
subject: "BLK-124 complete — tool result caching. 1069 tests. Content-addressed, two-level LRU + disk."
date: 2026-08-08T12:45:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_2220_mgmt-to-backend_blk127-confirmed.md
message-id: 2026-08-08_1245_backend-to-mgmt_blk124-complete
---

## BLK-124 — Tool Result Caching — Complete

### What was built

**1. Content-addressed cache** (`src/tools/cache.py`)
- Cache key: `sha256(cache_version + tool_name + sha256(image_bytes) + canonical_json(params) + provider)`
- Hashes **image region bytes**, not file paths — identical pixels from different bboxes hit the same entry
- Cache version prefix (`v1`) for clean invalidation on provider upgrades

**2. Two-level cache**
- In-memory bounded LRU (default 256 entries)
- File-based store under `.adep/cache/{key[:2]}/{key}.json`
- Disk persistence across restarts
- LRU size eviction (default max 2 GB)

**3. ToolSpec.cacheable flag** (`src/tools/base.py`)
- Default `False` — caching is opt-in per tool
- `ToolRegistry.call()` checks cache before invoking, stores result after

**4. Cacheable tools marked**
- `ocr`, `detect_layout`, `vlm`, `read_table`, `read_chart`, `crop`, `deskew`, `read_tag`

**5. TTL expiry**
- Default 30 days, configurable via `ADE_CACHE_TTL_SECONDS`
- Expired entries purged on access

**6. Config settings** (`src/config.py`)
- `cache_enabled` (default `true`) — disable for tests
- `cache_ttl_seconds` (2,592,000 = 30 days)
- `cache_max_size_bytes` (2 GB)
- `cache_memory_entries` (256)
- `cache_version` ("v1")

**7. Admin API endpoints**
- `GET /api/v1/admin/cache/stats` — hits, misses, evictions, memory_entries, disk_entries, total_size_bytes, hit_rate
- `DELETE /api/v1/admin/cache` — purge all entries

### Test Results

```
1069 passed, 7 deselected, 2 warnings in 65.93s
```

**26 new tests** in `src/tests/test_cache.py`:
- 7 cache key computation tests (deterministic, tool/params/image/provider differentiation, identical-bytes-same-key)
- 3 ToolCache get/put/stats tests
- 2 TTL expiry tests
- 2 LRU eviction tests (memory bound, access order)
- 2 disk persistence tests
- 1 cache clear test
- 2 ToolSpec.cacheable flag tests
- 3 ToolRegistry.call() caching tests (cacheable, non-cacheable, disabled)
- 1 cache version invalidation test
- 1 cached-second-run-zero-provider-calls test
- 2 API endpoint tests (stats, clear)

### Spec

Moved to `implemented/features/BLK-124_tool-result-caching.md`.
