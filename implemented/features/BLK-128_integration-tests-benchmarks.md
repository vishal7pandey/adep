---
id: BLK-128
type: feature
title: "Real-provider integration test suite + performance benchmarks"
priority: high
status: done
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: L
depends-on: [BLK-124]
tags: [backend, testing, integration, benchmarks, quality]
---

## Problem

All 754 tests use mocked providers. BLK-103 added 9 e2e tests — also
mocked. **Nothing has ever verified that the platform extracts
correctly against real OCR and real VLM calls.**

Mocked tests prove the plumbing works. They cannot catch:
- Prompts that confuse the actual model
- Confidence scores that are miscalibrated
- Probe orders that waste cycles on real documents
- Invariants that fail because real extraction returns different
  shapes than the mocks assume
- Token/cost estimates that are wrong by an order of magnitude

We have zero ground truth on accuracy. We cannot answer "does this
work?" or "did that change make it better or worse?"

## Requirements

### 1. Labelled Ground-Truth Fixtures

For each sample document in `sample-data/`, create a sibling
`{name}.expected.json` with the correct field values:

```json
{
  "document": "sample-data/invoices/acme-invoice-001.pdf",
  "definition_id": "def-invoice",
  "expected": {
    "invoice_number": "INV-2024-0042",
    "total": 1250.00,
    "invoice_date": "2024-03-15"
  },
  "tolerances": { "total": 0.01 },
  "min_confidence": { "invoice_number": 0.85 }
}
```

mgmt owns producing the labels (BLK-104 covers expanding sample data).
Backend owns the harness that consumes them.

### 2. Integration Test Suite

`src/tests/test_integration_real.py`, all marked
`@pytest.mark.integration`:

- Skipped by default and in CI
- Run explicitly: `uv run pytest -m integration`
- Require real credentials; skip with a clear message if absent
- Assert per-field correctness against the expected JSON, honouring
  tolerances
- Assert confidence meets the declared minimums
- Assert the run terminates within the cycle caps
- Assert grounding bboxes are present and land inside the page bounds

### 3. Accuracy Report

Produce a machine-readable report per integration run:

```json
{
  "run_at": "...",
  "documents_tested": 12,
  "field_accuracy": 0.94,
  "exact_match_rate": 0.87,
  "avg_confidence": 0.89,
  "confidence_calibration_error": 0.06,
  "avg_cycles": 8.2,
  "avg_cost_usd": 0.042,
  "per_field": { "invoice_number": {"accuracy": 1.0, "avg_confidence": 0.93} },
  "failures": [ ... ]
}
```

Write to `.adep/reports/accuracy_{timestamp}.json`. This wires into
the existing evaluation harness (BLK-015) rather than duplicating it.

### 4. Confidence Calibration Check

Critical and currently unmeasured: **are the confidence scores
meaningful?** Bucket predictions by reported confidence and compare
against actual correctness. If fields reported at 0.9 confidence are
only 60% correct, the scores are lying and every downstream
threshold is wrong.

Report expected calibration error. Flag any bucket where
|reported − actual| > 0.15 as a calibration failure.

### 5. Performance Benchmarks

`src/tests/test_benchmarks.py`, also integration-marked:

| Metric | Target |
|--------|--------|
| Single-page invoice, cold cache | < 30 s |
| Single-page invoice, warm cache | < 3 s |
| 10-page document | < 120 s |
| Tool registry lookup | < 1 ms |
| Definition store list (100 defs) | < 50 ms |
| SSE first byte after run start | < 500 ms |

Record results to `.adep/reports/benchmarks_{timestamp}.json` so
regressions are visible over time.

## Acceptance Criteria

- [ ] `.expected.json` schema defined and documented
- [ ] Integration suite marked `@pytest.mark.integration`, skipped by default
- [ ] Clear skip message when credentials are absent
- [ ] Per-field assertions with tolerance support
- [ ] Confidence-minimum assertions
- [ ] Grounding bbox validity assertions
- [ ] Accuracy report written to `.adep/reports/`
- [ ] Confidence calibration measured with expected calibration error
- [ ] Calibration failures flagged when |reported − actual| > 0.15
- [ ] Benchmark suite with the 6 metrics above
- [ ] Benchmark results persisted for trend comparison
- [ ] Wired into the BLK-015 evaluation harness, not duplicated
- [ ] `README` section documenting how to run integration tests
- [ ] No regression in the 754 mocked tests

## Constraints

- Integration tests must **never** run in CI by default — they cost
  real money
- Must not commit real credentials or API responses containing
  customer data
- Skip cleanly rather than fail when credentials are missing

## Notes

Depends on BLK-124 (caching) so the warm-cache benchmark is
meaningful. Depends on mgmt delivering labelled fixtures — I will
prioritise that under BLK-104.

**This is the most important quality item in the backlog.** Until it
lands we are shipping on faith.
