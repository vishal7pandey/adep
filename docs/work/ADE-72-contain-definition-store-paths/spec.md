# ADE-72 — Contain definition store paths (CodeQL py/path-injection, 13 alerts)

Status: draft · Risk: high · Jira: ADE-72
<!-- Security finding: neutral wording on purpose; this repo is public. -->

Grouped code-scanning findings of rule `py/path-injection` (high), all in `src/definitions/store.py`: alerts 11 to 23 (lines 47, 48, 56 x2,
59 in `_atomic_write`; 70, 78 in `_atomic_create`; 151, 153 `read`; 162 `update`; 175, 177 `delete`; 196 `exists`).

## Repro

Environment: `master` @ 063fead.

A definition, skill, template or run id from the URL or request body flows into `self.base_dir / entity_type / f"{id}.json"` and into
`exists()`, `read_text()`, `os.open`, `mkstemp`, `os.replace`, `unlink`. The id is checked by a regex in `_path_for`, which CodeQL
does not recognise as a sanitizer; `entity_type` is not checked at all; a symlinked file or directory inside the store can lead out
of it.

Automated repro (failing on current code), `uv run python -m pytest src/tests/test_definition_store_containment.py -q` (27 failed,
70 passed before the fix):

- `TestEntityTypeIsContained`: an entity type such as `../outside` is accepted by every operation (reads, creates, updates and deletes
  files outside the store).
- `TestRoutesAnswerAnInvalidIdWithA4xx`: GET, PUT and DELETE of `/definitions`, `/skills`, `/templates` and `/runs` with an invalid id,
  and POST `/definitions` with an invalid body id, raise an unhandled `ValueError` (HTTP 500) instead of a 4xx.

Honest note: id traversal (`../x`, absolute, separators) is already refused by the regex on every operation; those tests pass before and
after and pin the behaviour. The symlink tests exercise the new guard (a Windows directory junction is used where symlinks are not
permitted; the file-symlink test skips there and runs on Linux CI).

Reproducibility: always (CodeQL reports the 13 alerts on every analysis; the 500s are deterministic).

## Expected

Every public store operation (create, read, update, delete, exists, and the typed wrappers over them) validates the entity type against
the known types and the id against the id pattern, resolves the target with `os.path.realpath`, and touches the file only inside the
true branch of one inline `startswith(root + os.sep)` guard on the realpath of the store root. A bad type or id raises
`InvalidEntityIdError` (a `ValueError` subclass, message still `Invalid entity ID ...`); the API answers it with 400. Legitimate ids,
built-in definitions, skills and templates keep working.

## Actual

Containment is by regex on the id only; the entity type and symlinks are unchecked; `ValueError` escapes the routes as HTTP 500.

## Root cause (with evidence)

- Where: `src/definitions/store.py:40-80,107-198`; callers in `src/api/routes/{definitions,skills,templates,runs}.py`.
- Why: the path is built from request values with no guard the analyzer recognises, and the type is trusted; callers handle only
  `FileNotFoundError`.
- Introduced by: BLK-017 (store), BLK-151 (regex).
- Evidence: alerts 11 to 23 state `open`; the failing tests above.

## Blast radius

All routes over definitions, skills, templates and runs, `run_engine`, `run_executor`, `batches`. `DatabaseDefinitionStore` (SQLite) has
no file paths; it only gets the same exception type for its id check. The helpers `_atomic_write` / `_atomic_create` now take a string
path (a `Path` still works). `src/agent/webhooks.py` has its own helper and is ADE-71.

## Regression criterion (AC1)

AC1: The failing tests listed under Repro pass after the fix; `test_definition_store_containment.py`, `test_audit_fixes.py`,
`test_db_store.py`, `test_path_containment.py` and the rest of the suite stay as before (the same 12 environment failures as unmodified
master in the shared venv, 2 of them the known ADE-23/ADE-24).

AC2: After the merge and the push scan, alerts 11 to 23 each re-query as `fixed` on master, and the PR CodeQL result check shows no new
alert. Any alert that stays open after a demonstrably safe fix gets a dismissal proposal on ADE-72, never a dismissal by the agent.

## Fix constraints

- `os.path.realpath` on the store root and the candidate, then ONE inline `startswith(root + os.sep)` guard per operation whose true
  branch holds the file operation; no helper that returns a checked string, no `Path.resolve()` / `parents` forms. The atomic helpers
  receive only the guarded string.
- Keep `ValueError` compatibility and the `Invalid entity ID` message; `FileNotFoundError` / `FileExistsError` semantics unchanged.
- The 400 mapping is one app-level exception handler for `InvalidEntityIdError`, not per route.

## Risks

Risk high (path handling, many callers). A store directory that is a symlink to somewhere outside `.adep` stops working (intended).
Rollback: revert the merge commit.
