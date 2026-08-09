---
id: BLK-015
type: feature
title: "Evaluation harness — grounded accuracy + confidence calibration"
priority: low
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-013]
tags: [evaluation, quality, metrics]
---

## Description

Build an evaluation harness that measures grounded accuracy and confidence
calibration on a small held-out set per document type. Produces a report
showing per-field accuracy, grounding precision, and confidence-vs-accuracy
calibration curves.

Incorporates industry-standard multimodal benchmarks:
- **ANLS** (Average Normalized Levenshtein Similarity): partial credit for
  near-matches based on edit distance. Standard for DocVQA evaluation.
- **SMuDGE** (Semantics and MUltimodal Document Grounded Evaluation): factors
  in spatial localization and expected output type (numeric vs textual).
  Addresses ANLS's blind spot — a model can achieve high ANLS by
  hallucinating a correct number without actually locating it on the page.

ADEP's grounding requirement aligns perfectly with SMuDGE — every
extracted value is tethered to a bbox, satisfying the most rigorous
standards for enterprise auditability.

## Acceptance Criteria

- [ ] Evaluation script that runs extraction on a fixture set
- [ ] Grounded accuracy metric (field value correct + bbox overlaps ground truth)
- [ ] ANLS metric implemented (Normalized Levenshtein Similarity per field)
- [ ] SMuDGE-style metric: spatial localization score (IoU with ground truth bbox)
- [ ] Confidence calibration metric (confidence vs actual accuracy)
- [ ] Per-field breakdown in report
- [ ] Per-sector breakdown (if multiple skills/templates tested)
- [ ] HTML or JSON report output
- [ ] Support for multi-page document evaluation (MP-DocVQA style)
- [ ] Chart extraction evaluation (ChartQA-style numerical series comparison)

## Benchmarks Reference

| Benchmark | Focus | ADEP Relevance |
|-----------|-------|----------------|
| DocVQA | Single-page diverse layouts | Baseline extraction accuracy |
| MP-DocVQA | Multi-page sequential | Hierarchical state (BLK-041) |
| DUDE | Multi-domain QA | Field-driven working set |
| ChartQA | Chart/infographic interpretation | read_chart tool (BLK-040) |
| OmniMapBench | Map/spatial reasoning | Pixel grounding validation |
| SMuDGE | Grounded evaluation | Bbox IoU + output type checking |

## Dependencies

- BLK-013 (run() to execute extractions)

## Notes

- vision.md §10 Phase 1 step 6
- ADE industry mapping: §State-of-the-Art Evaluation Metrics
- Deferred to Phase 4 (not blocking Phase 3 frontend work)
