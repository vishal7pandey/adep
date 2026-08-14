---
id: BLK-174
type: feature
title: "Real-world benchmark suite for extraction quality and provider comparison"
priority: high
status: backlog
phase: 4
owner: unassigned
created: 2026-08-09T09:20:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-104]
tags: [evaluation, benchmarks, providers, accuracy, confidence, regression]
---

## Description

The project has a strong test harness for unit-level logic, but it does not yet have a robust real-world evaluation pipeline that measures extraction quality against labeled documents and provider differences. The current status notes explicitly mention that "all tests are mocked" and that accuracy and confidence calibration have never been measured against real providers.

This backlog item closes that gap by adding a benchmark suite that compares extraction performance across providers, document types, and confidence thresholds using labeled fixture sets from `sample-data/` and a repeatable regression dashboard.

## Motivation

The platform is designed around grounded extraction, variable OCR/VLM providers, and confidence thresholds. Without a benchmark suite, the team cannot answer basic questions like:

- Which provider is best for this document family?
- Which model fails on low-quality scans?
- What confidence thresholds are safe to enforce?
- Did a change improve or regress extraction accuracy?

This is a material product requirement, not only an engineering nicety.

## Acceptance Criteria

- [ ] Benchmark runner can evaluate a set of labeled documents against a chosen provider stack
- [ ] Output includes precision/recall, field-level success rate, grounding coverage, and token/cost metrics
- [ ] Comparison dashboard can rank provider configurations side-by-side
- [ ] Runs can be saved as regression snapshots over time
- [ ] Benchmark failures block promotion of provider or skill changes when configured thresholds are exceeded
- [ ] Benchmark command is documented in project README and CI workflow

## Constraints

- Must work with both local and cloud-backed providers
- Needs a curated set of labeled fixtures derived from `sample-data/` and ground-truth files
- Benchmarking should be deterministic and repeatable; no hidden mock values

## Dependencies

- BLK-104 (expand sample data + ground-truth labels)
- BLK-128 (benchmarking and evaluation strategy foundations)
- provider adapters and template definitions

## Notes

- Project status explicitly calls this out as an open gap: "All tests are mocked. Accuracy and confidence calibration have never been measured against real providers."
- This item connects directly to the platform’s claim that output is grounded, verifiable, and confidence-aware.

## Implementation Log

- **2026-08-09T09:20 (mgmt)**: Logged from repo audit and project status review; benchmark gap is one of the clearest remaining product-level risks.
