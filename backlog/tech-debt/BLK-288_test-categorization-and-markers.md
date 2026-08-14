---
id: BLK-288
type: tech-debt
title: "55 backend test files but no test categorization or markers — integration tests silently skipped in CI"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T13:20:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [testing, ci, pytest, quality, markers]
---

## Description

The backend has 55 test files in `src/tests/`, including:
- Unit tests (mocked providers, testing individual modules)
- Integration tests (`test_integration_real.py`, `test_integration_harness.py`) that require real Azure OpenAI providers
- E2E tests (`test_e2e.py`) that test the full extraction pipeline
- Feature-specific tests (`test_wave6.py`, `test_wave7.py`, `test_audit_fixes.py`, `test_reviewer_fixes.py`, `test_stabilization.py`)

The `pyproject.toml` defines `integration` markers, and CI runs `pytest -m "not integration"` to skip integration tests. But:

1. Many test files don't use markers at all — they run in CI whether they should or not
2. `test_integration_real.py` has a `pytest.importorskip` or skip-if-no-provider pattern, but other tests that need providers may not
3. Wave-based test files (`test_wave6.py`, `test_wave7.py`) have unclear scope — are they unit or integration?
4. `test_audit_fixes.py` and `test_reviewer_fixes.py` are regression tests for specific audit findings — they should be categorized
5. No `@pytest.mark.unit` markers exist — there's no positive categorization, only negative (`not integration`)

## Problem Statement

- CI runs `pytest -m "not integration"` but many tests that need providers or external services aren't marked as `integration`, causing silent skips or confusing failures
- Test categorization is ad-hoc — file names hint at purpose but there's no enforced taxonomy
- A developer can't easily run "just unit tests" or "just e2e tests" without knowing the file names
- The 55 test files are a flat list with no `conftest.py`-level organization or test discovery configuration
- Some tests may be testing dead code (e.g., `test_guardrails.py` tests guardrails that are dead code per BLK-179; `test_hitl.py` tests HITL that is unwired per BLK-204)

## Acceptance Criteria

- [ ] Add `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.regression` markers to all test files
- [ ] Update `pyproject.toml` to register all custom markers
- [ ] Update CI to run `pytest -m "unit or regression"` for PRs and `pytest -m "not integration"` for main branch
- [ ] Add a `make test-unit`, `make test-integration`, `make test-e2e` target to the Makefile
- [ ] Audit tests for dead code modules — mark tests for dead code with `@pytest.mark.dead_code` and exclude from CI
- [ ] Consider splitting `src/tests/` into `src/tests/unit/`, `src/tests/integration/`, `src/tests/e2e/` subdirectories

## Constraints

- Don't delete tests for dead code — they document expected behavior if the code is ever wired in
- Marker changes should be backwards-compatible with existing CI commands

## Dependencies

- `src/tests/` (all 55 test files)
- `pyproject.toml` (pytest config)
- `.github/workflows/ci.yml`
- `Makefile`
- Related to BLK-179 (guardrails dead code), BLK-204 (HITL unwired) — their tests exist but test dead code

## Notes

- Found during full-repo audit; the test suite is large but uncategorized, making it hard to understand what's actually being tested in CI

## Implementation Log

- **2026-08-09T16:00 (mgmt)**: Reassigned from `cline` (mandate suspended, see projectmgmt/STATUS.md 2026-08-09 16:00 note) to `devin`. Test-code ownership for this file's domain reverts to the implementing team; independent verification now happens via cross-team review (devin<->antigravity) instead of a dedicated gate.

- **2026-08-09 (mgmt)**: Assigned to `cline` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
