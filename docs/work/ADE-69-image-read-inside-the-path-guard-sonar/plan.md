# ADE-69 — Image read inside the path guard (Sonar S2083 re-raised)

Status: draft · Risk: high · Jira: ADE-69
Created: 2026-10-07 · Slug: image-read-inside-the-path-guard-sonar · Spec: spec.md

## Summary

Rewrite `_encode_image` so each allowed root has its own inline `startswith(root + os.sep)` check whose true branch reads, encodes
and returns, and the refusal follows the loop. Same behaviour, scanner-visible sanitizer.

**Size:** S

## Current state

`src/providers/vlm_azure.py` `_encode_image` (lines 65-85): computes `working_root`, `temp_root`, `real_path`, picks
`root = temp_root if ... else working_root`, raises if `not real_path.startswith(root + os.sep)`, then opens `real_path`.
Tests: `src/tests/test_sonar_path_containment.py`. Run with `uv run python -m pytest ...`.

## Approach

For each `root` in `(working_root, temp_root)`: `if real_path.startswith(root + os.sep):` open, encode and return the data URI
inside the true branch. After the loop: `raise ImagePathNotAllowed("Image path is outside the allowed directories")`.

**Alternatives rejected**
- `Path.resolve()` with `is_relative_to` / `parents`: CodeQL does not recognise it (learned on PR #24).
- Two unrolled `if` blocks duplicating the read: more code, same effect; revisit only if Sonar rejects the loop form.
- A helper function: hides the sanitizer from the scanner.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Add the two sibling-prefix tests | `src/tests/test_sonar_path_containment.py` | AC1 | they pass before and after (behaviour already correct) |
| T2 | Restructure `_encode_image` | `src/providers/vlm_azure.py` | AC1 | the tests in the file pass; mutation audit |
| T3 | Full suite, ruff, PR scan: Sonar PR issues and CodeQL check | none | AC1, AC2 | baseline 2 failures; no new Sonar or CodeQL issue on the PR |
| T4 | After merge and push scan read the Sonar issue | none | AC2 | API shows CLOSED |

## Data, API and migration impact

None.

## Security and failure modes

Same refusal behaviour (`ImagePathNotAllowed`, not retried). No new inputs.

## Rollout and rollback

Merge via PR; revert the merge commit to undo.

## Risks and open points

Sonar may still report the loop form; then try the unrolled form, and if it still reports a demonstrably safe sink, propose a
dismissal to the owner (not applied).
