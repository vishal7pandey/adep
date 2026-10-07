# ADE-70 — Pin paddleocr below 3

Status: draft · Risk: medium · Jira: ADE-70
Created: 2026-10-07 · Slug: pin-paddleocr-below-3 · Spec: spec.md

## Summary

Restore `paddleocr` 2.x (pin `>=2.7,<3`, relock to 2.10.0), prove it with a guard test and a non-mocked contract test, and
tell Dependabot not to propose a paddleocr major again.

**Size:** S

## Current state

`pyproject.toml:30` has `paddleocr>=3.7.0`; `uv.lock` resolves 3.7.0. `src/providers/ocr_paddle.py` uses the 2.x API.
Tests for the provider mock the engine. `.github/dependabot.yml` has no ignore rules.

## Approach

1. Edit `pyproject.toml` to `paddleocr>=2.7,<3` and run `uv lock`; make sure `paddleocr` is 2.10.0 and the diff only reflects
   the 2.x dependency set. Sync the worktree venv with `uv sync --frozen --all-extras`.
2. Add `src/tests/test_paddleocr_contract.py`: (a) guard reading the installed version via `importlib.metadata` and the
   `uv.lock` entry, failing on 3.x; (b) a contract test against the installed class that does not download models.
3. Add the Dependabot `ignore` entry (`dependency-name: paddleocr`, `update-types: ["version-update:semver-major"]`) under the
   `uv` ecosystem, with a comment.

**Alternatives rejected:** migrating the provider to 3.x (`predict`, result objects): bigger, and the old engine goes
away with ADE-33; keeping 3.x and mocking harder: does not fix runtime.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Add tests (fail on 3.7.0 first) | `src/tests/test_paddleocr_contract.py` | AC1 | run on current env: fail |
| T2 | Pin and relock, sync | `pyproject.toml`, `uv.lock` | AC2 | tests pass, `uv sync --frozen --all-extras` ok |
| T3 | Dependabot ignore | `.github/dependabot.yml` | AC3 | YAML valid, diff is that block only |
| T4 | Full suite, PR, CI incl. CodeQL and sonarcloud | none | AC1-3 | baseline 2 failures (ADE-23, ADE-24) |

## Data, API and migration impact

None. Environments rebuilt from the lockfile get 2.10.0 and its dependency set.

## Security and failure modes

Changes the dependency set (3.x pulls different packages than 2.x); the lockfile diff is reviewed. No secrets.

## Rollout and rollback

Merge via PR; revert the merge commit to undo.

## Risks and open points

The lockfile may re-resolve other packages; keep `uv lock` minimal and read the diff. Whether the 2.x constructor can be
exercised without model downloads is checked in T1 (otherwise the contract test inspects the signature and arguments only).
