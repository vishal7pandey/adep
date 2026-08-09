---
from: backend
to: mgmt
subject: "BLK-128 complete — integration tests + benchmarks. 1104 tests + 19 integration. Wired into BLK-015."
date: 2026-08-08T13:00:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_2225_mgmt-to-backend_blk124-confirmed.md
message-id: 2026-08-08_1300_backend-to-mgmt_blk128-complete
---

## BLK-128 — Integration Tests + Benchmarks — Complete

### What was built

**1. Expected fixture loader** (`src/eval/fixtures.py`)
- `ExpectedFixture` dataclass: document_path, definition_id, expected fields, tolerances, min_confidence
- `load_expected_fixtures()` — recursively loads `*.expected.json` from sample-data/
- `values_match_with_tolerance()` — numeric tolerance + case-insensitive string match
- `check_bbox_in_page_bounds()` — validates grounding bboxes within page dimensions

**2. Accuracy report writer** (`src/eval/accuracy.py`)
- `AccuracyReport` — full report with field_accuracy, exact_match_rate, avg_confidence, ECE, avg_cycles, avg_cost_usd, per_field stats, failures
- `CalibrationBucket` — confidence buckets with avg_confidence vs actual_accuracy, is_failure flag when |reported - actual| > 0.15
- `compute_expected_calibration_error()` — ECE metric across 5 buckets [0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0]
- `build_accuracy_report()` — extends BLK-015 EvaluationReport with calibration and failures
- `save_accuracy_report()` — writes to `.adep/reports/accuracy_{timestamp}.json`

**3. Benchmark suite** (`src/eval/benchmarks.py`)
- 6 benchmark targets: cold cache (<30s), warm cache (<3s), 10-page (<120s), tool registry lookup (<1ms), definition store list 100 (<50ms), SSE first byte (<500ms)
- `time_operation()` utility, `BenchmarkResult`/`BenchmarkReport` dataclasses
- `save_benchmark_report()` — writes to `.adep/reports/benchmarks_{timestamp}.json`

**4. Integration test suite** (`src/tests/test_integration_real.py`)
- 7 tests marked `@pytest.mark.integration`:
  - Field accuracy with tolerance
  - Confidence minimums
  - Grounding bbox presence
  - Run terminates within cycle caps
  - Accuracy report generated and saved
  - Confidence calibration (ECE + bucket failure flagging)
  - Cached second run zero provider calls
- Skip cleanly when credentials or fixtures missing

**5. Benchmark tests** (`src/tests/test_benchmarks.py`)
- 5 benchmark tests (2 non-provider, 3 provider-required):
  - Tool registry lookup < 1ms (always runnable)
  - Definition store list 100 defs < 50ms (always runnable)
  - Single-page cold cache < 30s (requires credentials)
  - Single-page warm cache < 3s (requires credentials)
  - SSE first byte < 500ms (requires credentials)

**6. Harness unit tests** (`src/tests/test_integration_harness.py`)
- 35 unit tests (NOT integration-marked, run in CI):
  - Fixture loader (5 tests)
  - Value matching with tolerance (8 tests)
  - BBox validation (6 tests)
  - Confidence calibration (5 tests)
  - Accuracy report generation (4 tests)
  - Benchmark utilities (5 tests)
  - Integration marker verification (2 tests)

**7. Wired into BLK-015**
- Uses existing `run_evaluation()`, `EvaluationReport`, `FieldMetric` from `src/eval/harness.py`
- Extends with calibration buckets and failure details rather than duplicating

**8. README updated** with integration test documentation, prerequisites, and skip behavior

### Test Results

```
1104 passed, 19 deselected, 2 warnings in 70.28s
```

- 1104 non-integration tests pass (including 35 new harness tests)
- 19 integration tests deselected (skip in normal CI — require real credentials + fixtures)
- 0 failures

### Coordination Note

Waiting on mgmt for `.expected.json` fixtures under BLK-104. Integration tests will activate automatically once fixtures are placed in `sample-data/` and credentials are set.

### Spec

Moved to `implemented/features/BLK-128_integration-tests-benchmarks.md`.
