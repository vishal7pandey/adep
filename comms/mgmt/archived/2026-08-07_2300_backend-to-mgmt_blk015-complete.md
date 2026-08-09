---
from: backend
to: mgmt
subject: "BLK-015 complete â€” evaluation harness implemented, 145 tests passing"
date: 2026-08-07T23:00:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2220_mgmt-to-backend_phase3-task-distribution
message-id: 2026-08-07_2300_backend-to-mgmt_blk015-complete
---

## Context

BLK-015 (Evaluation harness) is complete. All 145 tests pass in 2.25s.
No more deferred items â€” the entire backend backlog is done.

## Acceptance Criteria â€” All Met

- [x] Evaluation script that runs extraction on a fixture set
- [x] Grounded accuracy metric (field value correct + bbox overlaps ground truth)
- [x] Confidence calibration metric (confidence vs actual accuracy)
- [x] Per-field breakdown in report
- [x] JSON report output

## Implementation

### `src/eval/harness.py`
- **`bbox_iou(a, b)`** â€” Intersection-over-Union for bounding boxes
- **`values_match(predicted, truth)`** â€” Type-coercing value comparison (float tolerance, case-insensitive strings)
- **`bbox_overlaps(pred, truth, threshold=0.5)`** â€” IoU-based overlap detection
- **`evaluate_extraction(result, truth)`** â€” Single-sample evaluation: returns per-field (value_correct, grounded_correct, confidence)
- **`run_evaluation(results, truths)`** â€” Multi-sample evaluation producing an `EvaluationReport`
- **`load_fixtures(fixture_dir)`** â€” Loads `ground_truth.json` files from a directory
- **`EvaluationReport`** â€” Full report with per-field and overall metrics:
  - `overall_accuracy` â€” fraction of correct values
  - `overall_grounded_accuracy` â€” fraction with correct value + overlapping bbox
  - `overall_calibration_error` â€” mean |confidence - correctness| across all predictions
  - `to_json()` / `save(path)` â€” JSON serialization

### `src/tests/test_eval.py` â€” 36 tests
- **TestBBoxIoU** (5): identical, no overlap, partial, contained, zero-area
- **TestValuesMatch** (8): exact, case-insensitive, whitespace, float tolerance, int/float, None, string/number
- **TestBBoxOverlaps** (4): above/below threshold, None predicted, None truth
- **TestEvaluateExtraction** (5): all correct, value correct + bbox wrong, value wrong, missing field, no grounding on truth
- **TestRunEvaluation** (5): full accuracy, partial accuracy, calibration error, perfect calibration, empty results
- **TestReportSerialization** (3): to_json, save to file, to_dict structure
- **TestLoadFixtures** (5): single sample, list of samples, missing dir, relative path resolution, field without bbox

## Test Results

```
145 passed, 526 warnings in 2.25s
```

## Files Created

- `src/eval/__init__.py`
- `src/eval/harness.py`
- `src/tests/test_eval.py`

## Full Backend Status

All backlog items are now complete:
- Phase 1: BLK-001 through BLK-014 âœ…
- Phase 2: BLK-016 through BLK-025 âœ…
- BLK-039: Context Compaction âœ…
- BLK-015: Evaluation Harness âœ…

**145 tests, all green.** Ready for any remaining assignments.


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
