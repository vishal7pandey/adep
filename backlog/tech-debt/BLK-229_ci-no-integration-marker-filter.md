---
id: BLK-229
type: tech-debt
title: "CI runs all tests without integration marker filter — integration tests may fail or be silently skipped"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T14:05:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [ci, testing, pytest, integration, markers]
---

## Description

The CI pipeline runs tests with:

```yaml
- name: Tests (pytest)
  run: uv run pytest src/tests/ -v --tb=short
```

No `-m "not integration"` marker filter is used. The `pyproject.toml` registers `integration` markers, but CI doesn't use them. This means:

1. Integration tests that require real Azure OpenAI providers will either fail (if they don't skip gracefully) or be silently skipped (if they use `pytest.importorskip` or `skip_if` patterns)
2. The coverage step also runs without marker filtering: `uv run pytest src/tests/ --cov=src --cov-report=term-missing --cov-fail-under=80`
3. If integration tests fail without providers, CI is red for reasons unrelated to the code change
4. If integration tests skip silently, coverage numbers may be inflated (skipped tests don't count against coverage)

## Problem Statement

- CI doesn't filter integration tests, leading to either false failures or silent skips
- The `--cov-fail-under=80` threshold may be met or missed depending on which tests skip, making the coverage gate non-deterministic
- There's no separation between "fast feedback" (unit tests) and "thorough verification" (integration tests) in CI
- A developer can't tell from CI output whether integration tests ran, skipped, or failed

## Acceptance Criteria

- [ ] Update CI to run `uv run pytest src/tests/ -v --tb=short -m "not integration"` for the main test step
- [ ] Add a separate integration test job that runs only on main branch pushes (not PRs) with `uv run pytest src/tests/ -m "integration"` (requires Azure provider secrets)
- [ ] Update the coverage step to also use `-m "not integration"` for deterministic coverage numbers
- [ ] Consider a separate coverage threshold for integration vs unit tests

## Constraints

- Integration tests require `AZURE_API_KEY` and `AZURE_CHAT_ENDPOINT` secrets — only available in main branch CI
- Don't lower the coverage threshold — fix the non-determinism instead

## Dependencies

- `.github/workflows/ci.yml`
- `pyproject.toml` (pytest markers)
- Related to BLK-220 (test categorization and markers)

## Notes

- Found during full-repo audit; the CI test step is too broad, mixing unit and integration tests without filtering

## Implementation Log

- **2026-08-09T16:00 (mgmt)**: Reassigned from `cline` (mandate suspended, see projectmgmt/STATUS.md 2026-08-09 16:00 note) to `devin`. Test-code ownership for this file's domain reverts to the implementing team; independent verification now happens via cross-team review (devin<->antigravity) instead of a dedicated gate.

- **2026-08-09 (mgmt)**: Assigned to `cline` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
