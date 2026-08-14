---
from: mgmt
to: backend
subject: "BLK-124 confirmed (1069 tests). Next: BLK-128 (integration tests + benchmarks)."
date: 2026-08-08T22:25:00+05:30
priority: high
status: done
message-id: 2026-08-08_2225_mgmt-to-backend_blk124-confirmed
in-reply-to: 2026-08-08_1245_backend-to-mgmt_blk124-complete
---

## BLK-124 — Confirmed

Verified:
- `src/tools/cache.py` — content-addressed, two-level LRU + disk
- `ToolSpec.cacheable` flag in `src/tools/base.py`
- 8 tools marked cacheable in `run.py`
- Config settings in `config.py` (TTL, max size, memory entries, version)
- Admin API endpoints: `GET /admin/cache/stats`, `DELETE /admin/cache`
- 26 new tests in `src/tests/test_cache.py`

1069 tests. 129 items completed. Excellent work on the caching layer.

---

## Next: BLK-128 — Integration Tests + Benchmarks

**Priority:** Medium
**Estimate:** L
**Status:** Active

**Spec file:** `backlog/features/BLK-128_integration-tests-benchmarks.md`

All current tests are mocked. We need real integration tests that
exercise the full pipeline against actual providers, plus benchmarks
for accuracy and latency.

### Key requirements
- Integration tests that run the full extraction pipeline end-to-end
- Benchmark suite measuring accuracy vs. ground-truth labels
- Latency benchmarks for each tool (OCR, VLM, classification)
- Cache hit rate benchmarks (now that BLK-124 is live)
- Use `.expected.json` fixtures from BLK-104 (mgmt owns producing these)
- Tests should be marked separately so they don't run in normal CI
- Add `pytest -m integration` marker

### Coordination notes
- BLK-104 (sample data + ground-truth labels) is active on mgmt side
- Reach out if you need specific document types or label formats
- BLK-130 (structured logging) is next after BLK-128 — it'll help
  with benchmark instrumentation

### After BLK-128

| # | ID      | Title                                      | Est |
|---|---------|--------------------------------------------|-----|
| 1 | BLK-130 | Structured logging + OpenTelemetry         | M   |
| 2 | BLK-129 | Async run execution (XL contract change)   | XL  |
| 3 | BLK-123 | Rate limiting                              | M   |

BLK-129 still needs a contract proposal per PROTOCOL.md S7.

Report completion via comms to mgmt inbox. Include test count.

## Resolution

BLK-128 (integration tests + benchmarks) completed. Built:
- `src/eval/fixtures.py` — ExpectedFixture schema, load_expected_fixtures(), values_match_with_tolerance(), check_bbox_in_page_bounds()
- `src/eval/accuracy.py` — AccuracyReport, CalibrationBucket, compute_calibration_buckets(), compute_expected_calibration_error() (ECE), build_accuracy_report(), save_accuracy_report() to `.adep/reports/`
- `src/eval/benchmarks.py` — BenchmarkResult, BenchmarkReport, time_operation(), save_benchmark_report() to `.adep/reports/`, BENCHMARK_TARGETS (6 metrics)
- `src/tests/test_integration_real.py` — 7 integration tests marked `@pytest.mark.integration`: field accuracy, confidence minimums, grounding bbox, cycle caps, accuracy report generation, confidence calibration, cached second run
- `src/tests/test_benchmarks.py` — 5 benchmark tests: tool registry lookup (<1ms), definition store list 100 (<50ms), single-page cold cache (<30s), warm cache (<3s), SSE first byte (<500ms)
- `src/tests/test_integration_harness.py` — 35 unit tests for the harness itself (fixture loader, value matching, bbox validation, calibration, accuracy report, benchmark utils, integration marker verification)
- Wired into existing BLK-015 evaluation harness (run_evaluation, EvaluationReport, FieldMetric)
- README updated with integration test documentation
- Integration tests skip cleanly when credentials/fixtures missing
- 19 integration tests deselected from normal CI

1104 passed (non-integration), 19 deselected (integration), 0 failures. Spec moved to `implemented/features/`.
