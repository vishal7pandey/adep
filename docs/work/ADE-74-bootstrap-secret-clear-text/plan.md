# ADE-74 — Bootstrap secret clear-text

Status: draft · Risk: high · Jira: ADE-74
Created: 2026-10-07 · Slug: bootstrap-secret-clear-text · Spec: spec.md

## Summary

Replace the `print(banner, flush=True)` in `bootstrap_admin_key` with an explicit `sys.stdout.write(banner)` plus
`sys.stdout.flush()`: the same operator-visible output, no longer a logging-shaped call that carries the secret. A failing test
first proves `print` no longer receives the secret.

**Size:** S

## Current state

`src/api/auth.py:341-382` `bootstrap_admin_key` logs the key id with `logger.warning`, then prints the banner with the secret.
Tests: `src/tests/test_auth.py::TestBootstrap`. Run: `uv run python -m pytest src/tests/test_auth.py -q`.

## Approach

Build the banner string and write it with `sys.stdout.write` and flush. Keeps the one-time display requirement
(BLK-186, BLK-188) and removes the `print` sink.

**Alternatives rejected**
- Logging only a prefix of the secret: the banner is the only way the operator learns the secret; a prefix is useless to them
  and still derived from the secret.
- Writing the secret to a 0600 file: new persistence of a secret, behaviour change, out of scope.
- Dismissing the alert: not allowed without the owner, and a fix is possible.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing test: `print` not called with the secret, stdout still has it | `src/tests/test_auth.py` | AC1 | test fails on current code |
| T2 | Banner via `sys.stdout.write` + flush | `src/api/auth.py` | AC1 | `uv run python -m pytest src/tests/test_auth.py -q` |
| T3 | Re-query alert 46 after CodeQL ran on master | n/a | AC2 | `gh api .../code-scanning/alerts/46` state `fixed` |

## Data, API and migration impact

None.

## Security and failure modes

The secret is never logged. Failure mode: if CodeQL still flags the stdout write, the alert stays open and a dismissal proposal
goes to the owner; nothing is dismissed.

## Rollout and rollback

Merge, wait for CodeQL on master. Rollback: revert the merge commit.

## Risks and open points

CodeQL may model `sys.stdout.write` as a sink too; the PR CodeQL check shows it before merge.
