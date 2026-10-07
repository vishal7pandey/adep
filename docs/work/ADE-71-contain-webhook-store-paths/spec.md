# ADE-71 — Contain webhook store paths (CodeQL py/path-injection, 14 alerts)

Status: draft · Risk: high · Jira: ADE-71
<!-- Security finding: neutral wording on purpose; this repo is public. -->

Grouped code-scanning findings of rule `py/path-injection` (high), all in `src/agent/webhooks.py`: alerts 29 to 42 (lines 154, 155, 163 x2,
166 in `_atomic_write`; 253 in `create`; 264, 266 in `get`; 277, 279 in `get_raw`; 297, 299 in `update`; 312, 314 in `delete`).

## Repro

Environment: `master` @ ae0d977.

A webhook id from the URL or the request body flows straight into `self.hooks_dir / f"{hook_id}.json"` and into `exists()`, `read_text()`,
`mkstemp`, `os.replace` and `unlink`. Unlike the definition and document stores, `WebhookStore` has no id validation at all, so
`POST /webhooks` with id `../x` writes `.adep/x.json`, and an absolute-looking id reaches paths outside `.adep` (the test run for such an id
hangs in `mkstemp` against the filesystem root on Windows).

Automated repro (failing on current code), `uv run python -m pytest src/tests/test_webhook_store_containment.py -q -k "not abs"`
(43 failed, 13 passed before the fix; the two absolute-id cases are left out of that run because they try to write at the drive root):

- `TestEveryOperationRejectsABadId`: create, get, get_raw, update and delete accept `../x`, `a/b`, `a.b`, ... instead of raising.
- `TestEveryOperationRejectsABadId::test_traversal_never_touches_a_file_outside_the_webhooks_dir`: update and delete reach a file next
  to the webhooks directory.
- `TestRoutesAnswerAnInvalidIdWithA4xx`: `POST /webhooks` with id `../escaped` returns 201 and writes `.adep/escaped.json`.

The symlink test for a hook file skips on accounts that may not create symlinks (a directory junction is used for the directory case); both
run on Linux CI.

Reproducibility: always.

## Expected

Every webhook operation validates the id against the same pattern as the other stores (`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`), resolves the target with
`os.path.realpath`, and touches the file only inside the true branch of one inline `startswith(root + os.sep)` guard on the store root. A bad id
raises `InvalidEntityIdError` (a `ValueError`, message `Invalid webhook ID ...`) and the API answers 400 (the app-level handler from ADE-72).
Legitimate ids keep working.

## Actual

No validation or containment; a crafted id reads, writes, overwrites or deletes JSON files outside `.adep/webhooks/`.

## Root cause (with evidence)

- Where: `src/agent/webhooks.py:146-166` (`_atomic_write`) and `WebhookStore._path` plus its five callers (`create`, `get`, `get_raw`, `update`,
  `delete`, lines 253-314).
- Why: the id was never treated as untrusted input; the store was written before BLK-151 added the regex to the other two stores.
- Introduced by: BLK-064; BLK-151 covered `DefinitionStore` and `DocumentStore` only.
- Evidence: alerts 29 to 42 state `open`; the failing tests above.

## Blast radius

Routes under `/webhooks` (create, get, update, delete, test) and `dispatch` through `get_raw`. `list()` and `get_all_for_event()` scan the
directory with a glob and take no id. `_atomic_write` is also imported by `test_reviewer_fixes.py` (a `Path` argument still works).
Existing webhook files whose ids contain characters outside the pattern (dots, spaces) would stop being addressable by id; none are created
by the tests or the frontend, and the other stores already had this rule.

## Regression criterion (AC1)

AC1: The failing tests listed under Repro pass after the fix (all 67 in `src/tests/test_webhook_store_containment.py`, including the absolute-id
cases); `test_wave7.py`, `test_reviewer_fixes.py`, `test_audit_fixes.py`, `test_webhook_emission.py` and the rest of the suite stay as before
(the same 12 environment failures as unmodified master in the shared venv, 2 of them the known ADE-23/ADE-24).

AC2: After the merge and the push scan, alerts 29 to 42 each re-query as `fixed` on master, and the PR CodeQL result check shows no new alert.
Any alert that stays open after a demonstrably safe fix gets a dismissal proposal on ADE-71, never a dismissal by the agent.

## Fix constraints

- `os.path.realpath` on the store root and the candidate, then ONE inline `startswith(root + os.sep)` guard per operation whose true branch holds
  the file operation; no helper that returns a checked string, no `Path.resolve()` / `parents` forms. `_atomic_write` receives only the guarded
  string.
- Reuse `InvalidEntityIdError` and the ADE-72 handler; no per-route handling.
- `FileNotFoundError` / `FileExistsError` semantics unchanged.

## Risks

Risk high (path handling and a behaviour change for odd ids). Rollback: revert the merge commit.
