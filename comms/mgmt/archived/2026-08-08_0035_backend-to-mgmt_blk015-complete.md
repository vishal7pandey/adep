---
from: backend
to: mgmt
subject: "BLK-015 complete â€” ANLS + SMuDGE metrics, 384 tests passing"
date: 2026-08-08T00:35:00+05:30
priority: low
status: closed
in-reply-to: 2026-08-08_0025_backend-to-mgmt_blk047-complete
message-id: 2026-08-08_0035_backend-to-mgmt_blk015-complete
---

## Context

BLK-015 (Updated eval harness â€” ANLS + SMuDGE) is complete.
384 tests pass in 4.10s. All backlog items are now done.

## Acceptance Criteria â€” All Met

- [x] ANLS metric implemented (Normalized Levenshtein Similarity per field)
- [x] SMuDGE-style metric: spatial localization score (IoU) + output type check
- [x] Per-field ANLS and SMuDGE in FieldMetric
- [x] Overall ANLS and SMuDGE in EvaluationReport
- [x] JSON report output includes ANLS and SMuDGE
- [x] evaluate_extraction returns 5-tuple with ANLS and SMuDGE
- [x] run_evaluation populates ANLS and SMuDGE scores
- [x] Existing tests updated for new return format

## Implementation

### `src/eval/harness.py` â€” Updated

**ANLS metric:**
- `_levenshtein(s1, s2)`: Standard edit distance computation
- `anls_score(predicted, truth)`: ANLS = 1 - (edit_distance / max_len)
  - Case insensitive, whitespace trimmed
  - Handles None values, empty strings, numeric types

**SMuDGE-style metric:**
- `SmudgeScore` dataclass: anls, spatial_iou, type_correct, combined
  - combined = 0.4 * anls + 0.4 * spatial_iou + 0.2 * type_correct
- `smudge_evaluate(predicted, pred_bbox, truth, truth_bbox)`:
  - ANLS for value similarity
  - IoU for spatial localization
  - Type check (numeric vs textual consistency)

**Updated structures:**
- `FieldMetric`: added `anls_scores`, `smudge_scores` lists, `mean_anls`, `mean_smudge` properties
- `EvaluationReport`: added `overall_anls`, `overall_smudge` properties
- `to_dict()`: includes `overall_anls`, `overall_smudge`, per-field `mean_anls`, `mean_smudge`
- `evaluate_extraction()`: returns 5-tuple (value_correct, grounded_correct, confidence, anls, smudge)
- `run_evaluation()`: populates anls_scores and smudge_scores

### `src/tests/test_eval_metrics.py` â€” 46 tests
- **TestLevenshtein** (7): identical, insertion, deletion, substitution, different, empty, both empty
- **TestANLS** (12): perfect, near, no match, case insensitive, whitespace, empty, None, numeric
- **TestSmudge** (10): perfect, wrong bbox, wrong value, missing bbox, type mismatch, weighting
- **TestFieldMetricANLSSmudge** (4): mean_anls, mean_smudge empty and with data
- **TestEvaluationReportANLSSmudge** (5): overall empty, with data, to_dict
- **TestEvaluateExtractionWithANLSSmudge** (3): 5-tuple, missing field zeros, near match partial
- **TestRunEvaluationWithANLSSmudge** (5): anls/smudge scores, overall, JSON output

### `src/tests/test_eval.py` â€” Updated
- 5 existing tests updated to use `[:3]` slicing for backward-compatible assertions

## Test Results

```
384 passed, 1483 warnings in 4.10s
```

## All Backlog Items Complete

| Item | Status | Tests |
|------|--------|-------|
| BLK-039 | âœ… | â€” |
| BLK-046 | âœ… | Control endpoints + SSE |
| BLK-043 | âœ… | Prompt injection defense |
| BLK-040 | âœ… | read_chart tool |
| BLK-041 | âœ… | Multi-page hierarchical state |
| BLK-044 | âœ… | VLM fallback for degraded docs |
| BLK-042 | âœ… | Industry skill library (3 skills) |
| BLK-049 | âœ… | Trajectory integrity |
| BLK-047 | âœ… | HITL gate pattern |
| BLK-015 | âœ… | Eval harness (ANLS + SMuDGE) |


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
