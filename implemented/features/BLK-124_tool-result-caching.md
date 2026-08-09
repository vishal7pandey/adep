---
id: BLK-124
type: feature
title: "Tool result caching — content-addressed cache for OCR, VLM, and layout calls"
priority: high
status: done
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: L
depends-on: []
tags: [backend, performance, caching, cost-reduction]
---

## Problem

Every tool call recomputes from scratch. There is no caching anywhere
in `src/tools/` or `src/providers/`.

Consequences:
- Re-running the same document re-pays the full OCR and VLM cost
- The ReAct loop often calls `ocr` on overlapping regions within a
  single run — each is a fresh call
- Iterative skill tuning (edit skill → re-run) is expensive and slow
- Evaluation harness runs (BLK-015) multiply the cost by the number
  of fixtures

For a platform whose whole value proposition includes cost control
(BLK-050, BLK-051), recomputing identical work is the largest
avoidable spend.

## Requirements

### Content-Addressed Cache Key

The key must be derived from everything that affects the result:

```
key = sha256(
    tool_name +
    tool_version +
    sha256(image_bytes_of_region) +
    canonical_json(tool_params) +
    provider_name +
    provider_model_version
)
```

Critical: hash the **image region bytes**, not the file path or bbox
coordinates. Two different bboxes that crop to identical pixels
should hit the same cache entry.

### Cache Backend

- v1: file-based under `.adep/cache/{key[:2]}/{key}.json`
- Two-level: in-memory LRU (bounded, default 256 entries) in front of
  the file store
- Store the result payload plus metadata: `created_at`,
  `tool_name`, `provider`, `hit_count`, `size_bytes`

### Cacheable vs Non-Cacheable

| Tool class | Cacheable |
|------------|-----------|
| `ocr`, `detect_layout`, `read_chart`, `read_tag` | Yes |
| `vlm` (deterministic params, temperature 0) | Yes |
| `vlm` (temperature > 0) | No |
| `crop`, `deskew`, geometry ops | Yes (cheap, but avoids re-encode) |
| Anything with side effects | No |

Each `ToolSpec` gains a `cacheable: bool` attribute. Default `False`
so caching is opt-in per tool and cannot silently corrupt results.

### Invalidation & Eviction

- TTL per entry, default 30 days, configurable
- Max total cache size, default 2 GB — LRU eviction by `last_used_at`
- Cache version prefix in the key so a provider upgrade invalidates
  cleanly
- `DELETE /api/v1/admin/cache` to purge (admin scope)
- `GET /api/v1/admin/cache/stats` — entry count, size, hit rate

### Observability

- Log every hit/miss at DEBUG with the tool name and key prefix
- Add `cache_hits` and `cache_misses` to the run's token usage summary
- Surface cost saved: `tokens_saved`, `cost_saved_usd` per run

## Acceptance Criteria

- [ ] Content-addressed key derived from region bytes + params + provider
- [ ] Two-level cache: bounded in-memory LRU + file store
- [ ] `ToolSpec.cacheable` flag, default False
- [ ] `ocr`, `detect_layout`, `read_chart` marked cacheable
- [ ] `vlm` cacheable only when temperature == 0
- [ ] TTL expiry + LRU size eviction
- [ ] Cache version prefix for clean invalidation
- [ ] `GET /api/v1/admin/cache/stats` and `DELETE /api/v1/admin/cache`
- [ ] `cache_hits`, `cache_misses`, `cost_saved_usd` in run summary
- [ ] Config: `ADE_CACHE_ENABLED` (default true), TTL, max size
- [ ] Tests: hit, miss, identical-pixels-different-bbox hit,
      TTL expiry, LRU eviction, version invalidation, stats endpoint
- [ ] Tests prove a cached second run makes zero provider calls
- [ ] No regression in existing tests

## Constraints

- **Correctness over hit rate.** A wrong cache hit is far worse than
  a miss. When in doubt, don't cache.
- Cache must be disable-able for tests that assert provider call counts
- Do not cache anything derived from a non-deterministic provider call
