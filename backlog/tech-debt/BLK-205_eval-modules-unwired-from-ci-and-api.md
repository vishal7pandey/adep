---
id: BLK-205
type: tech-debt
title: "src/eval/ modules (accuracy, benchmarks, fixtures, harness) are unwired — eval infrastructure exists but is not integrated into CI or API"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T12:00:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [dead-code, eval, accuracy, testing, process, backlog-integrity]
---

## Description

`src/eval/` contains four modules totaling ~36KB of code:
- `accuracy.py` (10KB) — grounded accuracy scoring and confidence calibration
- `benchmarks.py` (3.8KB) — benchmark suite definitions
- `fixtures.py` (4.3KB) — test fixture management
- `harness.py` (17.9KB) — full evaluation harness for grounded accuracy

None of these modules are imported by any production code path, API route, or CI pipeline. They are only imported by their own tests (`test_eval.py`, `test_eval_metrics.py`, `test_benchmarks.py`).

The `scripts/run_api_grounded_eval.py` script exists to run the eval harness, but it's a standalone script — not wired into CI, not exposed via API, and not referenced by any documentation beyond its own docstring.

Meanwhile, `BLK-128_integration-tests-benchmarks.md` sits in `backlog/implemented/features/` — marked as **implemented**.

## Problem Statement

- 36KB of evaluation infrastructure code exists but is never run in CI, never exposed via API, and never used to produce the accuracy claims the project makes
- The "integration tests and benchmarks" backlog item is marked as implemented, but the implementation is not integrated anywhere
- The `ADE_codebase_audit.md` already noted that accuracy claims are based on the PDF fallback (BLK-178), not on actual agent execution — the eval harness that could verify this is sitting unused
- This is the fifth instance of the "code exists but isn't wired in" pattern (after guardrails BLK-179, eval BLK-182, AI modules BLK-199, HITL BLK-204)

## Acceptance Criteria

- [ ] Either wire eval modules into CI (add a `make eval` target, add eval step to `ci.yml`) and expose eval results via API endpoints, or move BLK-128 back to `features/` and acknowledge the implementation is incomplete
- [ ] If wiring in: run eval harness against real fixtures in CI, publish results as artifacts, expose eval status via `/api/v1/admin/eval` endpoint
- [ ] If not wiring in: update BLK-128 status and document why the eval infrastructure was built but never integrated

## Constraints

- Running eval requires sample data and possibly LLM providers — CI may need to run eval with mocked providers or skip on PRs
- Don't delete the code — it's valuable infrastructure, just unwired

## Dependencies

- `src/eval/accuracy.py`, `src/eval/benchmarks.py`, `src/eval/fixtures.py`, `src/eval/harness.py`
- `scripts/run_api_grounded_eval.py`
- `backlog/implemented/features/BLK-128_integration-tests-benchmarks.md`
- Related to BLK-179, BLK-182, BLK-199, BLK-204 — same systemic pattern

## Notes

- Found during full-repo audit; BLK-182 already partially covers this, but BLK-182 focuses on the eval modules being unwired from the API. This item focuses on the backlog integrity issue (BLK-128 marked implemented) and the CI integration gap.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
