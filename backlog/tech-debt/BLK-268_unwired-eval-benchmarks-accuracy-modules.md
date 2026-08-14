---
id: BLK-268
type: tech-debt
title: "eval/benchmarks.py and eval/accuracy.py are built-but-unwired — no script or route calls them"
priority: low
status: backlog
phase: 4
owner: devin
created: 2026-08-09T10:20:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [eval, benchmarks, accuracy, dead-code, unwired]
---

## Description

Two modules in `src/eval/` were built to spec, have their own passing unit tests, and are never called from anywhere a person or CI job would actually run:

- `src/eval/benchmarks.py` — `BENCHMARK_TARGETS`, `BenchmarkResult`, report-saving to `.adep/reports/` (built for BLK-128). No `scripts/run_benchmarks.py` or equivalent exists; `grep -rln "eval.benchmarks" src` outside its own test file returns nothing.
- `src/eval/accuracy.py` — confidence-calibration reporting (`build_accuracy_report`, `compute_calibration_buckets`, `compute_expected_calibration_error`). It correctly depends on `eval/harness.py` (so it's not itself an island), but nothing calls *it* — no script, no route, no CLI entrypoint outside its own test.

This is the same "ticket implemented in the sense that code exists and tests pass, without the last step of connecting it to something runnable" pattern flagged in BLK-179 (guardrails), just lower stakes since these are reporting tools, not safety mechanisms.

## Problem Statement

Two credible-looking, well-tested evaluation modules exist and do nothing in practice. Anyone auditing "do we measure accuracy/calibration" or "do we have a benchmark suite" will find real code and real tests and reasonably assume the capability is live, when actually no one has ever run it end-to-end outside its unit test.

## Acceptance Criteria

- [ ] Either: add a thin CLI entrypoint (`scripts/run_benchmarks.py`, `scripts/run_accuracy_report.py`) that calls these modules against real fixtures, and document how to run them
- [ ] Or: fold both into the scope of BLK-174 (real-world benchmark suite) rather than building parallel/duplicate machinery — BLK-174 is already planning a benchmark runner and comparison dashboard; check whether `eval/benchmarks.py`/`eval/accuracy.py` can be the foundation instead of being rebuilt from scratch
- [ ] Whichever path is chosen, at least one script or CI step actually invokes these modules so "unused except by own test" stops being true
- [ ] `.adep/reports/` output format is documented if kept

## Constraints

- Don't duplicate effort with BLK-174 — resolve this ticket by wiring existing code into that feature's scope, not by building a second benchmark system
- Keep this low-effort; this is a wiring gap, not a design problem

## Dependencies

- `src/eval/benchmarks.py`, `src/eval/accuracy.py`, `src/eval/harness.py`
- BLK-174 (real-world benchmark suite) — likely supersedes/absorbs this ticket's scope
- BLK-104 (sample data expansion) — needed for meaningful benchmark fixtures either way

## Notes

- Found via full-repo audit (`ADE_codebase_audit.md`, §2 sidebar); confirmed still unwired as of 2026-08-09 (no `scripts/` entrypoint exists)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T10:20 (mgmt)**: Logged after confirming neither module has a non-test caller and no benchmark script exists in `scripts/`.
