# ADE-71 — Contain webhook store paths

Status: draft · Risk: high · Jira: ADE-71
Created: 2026-10-07 · Slug: contain-webhook-store-paths · Spec: spec.md

## Summary

Validate the webhook id and wrap every file operation of `WebhookStore` (create, get, get_raw, update, delete) in an inline realpath +
`startswith(root + os.sep)` guard, raising `InvalidEntityIdError` (answered 400 by the existing app handler).

**Size:** S

## Current state

`src/agent/webhooks.py`: `WebhookStore._path` builds `hooks_dir / f"{id}.json"` with no validation; `_atomic_write(path: Path, ...)` is used by
`create` and `update`. `InvalidEntityIdError` and the 400 handler exist since ADE-72 (`src/definitions/base.py`, `src/api/main.py`).
Tests: `test_wave7.py`, `test_reviewer_fixes.py`, `test_audit_fixes.py`, `test_webhook_emission.py`.
Run: `uv run python -m pytest src/tests -q -m "not integration"`.

## Approach

Remove `_path`; add `_check_id` (pattern) and per operation `root = os.path.realpath(self.base_dir)`,
`real = os.path.realpath(os.path.join(root, "webhooks", id + ".json"))`, `if real.startswith(root + os.sep):` do the operation, else raise.
`_atomic_write` takes a string (a `Path` still works) and uses `os.path` calls. Guarding against the store root, not the webhooks directory,
makes a symlinked webhooks directory fail as well.

**Alternatives rejected**
- A shared helper returning the checked path: the analyzer may not see the guard at the sink (ADE-51 to ADE-57 lessons).
- Per-route `try/except`: the app handler already covers it.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing regression tests | `src/tests/test_webhook_store_containment.py` | AC1 | 43 fail on current code |
| T2 | Id check, guards in the five operations, string-path `_atomic_write` | `src/agent/webhooks.py` | AC1, AC2 | store and route tests |
| T3 | PR CodeQL check, then re-query alerts 29-42 after the master scan | n/a | AC2 | `gh api .../alerts/<id>` |

## Data, API and migration impact

None for data. Ids outside `^[a-zA-Z0-9][a-zA-Z0-9_-]*$` are refused (400); an invalid id used to be accepted.

## Security and failure modes

Containment on every file operation; symlinks leaving the store are refused. Failure: 400 with the invalid-id message.

## Rollout and rollback

Merge, wait for CodeQL on master. Rollback: revert the merge commit.

## Risks and open points

CodeQL may still track taint into `_atomic_write`; the PR CodeQL result check shows it before merge, and the helper body can be inlined if
needed.
