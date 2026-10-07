# ADE-72 — Contain definition store paths

Status: draft · Risk: high · Jira: ADE-72
Created: 2026-10-07 · Slug: contain-definition-store-paths · Spec: spec.md

## Summary

Give every `DefinitionStore` operation an inline realpath + `startswith(root + os.sep)` guard around its file operation, validate the
entity type as well as the id, and map the new `InvalidEntityIdError` to HTTP 400 with one app-level handler.

**Size:** S

## Current state

`src/definitions/store.py`: `_path_for` (regex only) feeds `create/read/update/delete/exists`; `_atomic_write` / `_atomic_create` take a
`Path`. `db_store.py` has its own `ValueError` id check. Tests: `test_audit_fixes.py` (ValueError `Invalid entity ID`), `test_db_store.py`.
Run: `uv run python -m pytest src/tests -q -m "not integration"`.

## Approach

Replace `_path_for` with `_check_ids` (type in `_ENTITY_TYPES`, id matches the pattern) and per operation:
`root = os.path.realpath(self.base_dir)`, `real = os.path.realpath(os.path.join(root, type, id + ".json"))`,
`if real.startswith(root + os.sep):` do the operation (atomic helpers get the string), else raise. Guarding against the store root, not the
entity directory, makes a symlinked entity directory fail too. New `InvalidEntityIdError(ValueError)` in `definitions/base.py`, used by
both stores; handler in `create_app` returns 400.

**Alternatives rejected**
- A shared helper returning the checked path: the analyzer may not see the guard at the sink (ADE-51 to ADE-57 lessons).
- `try/except ValueError` in every route: many call sites (including `run_engine`), easy to miss one; a handler covers all.
- 404 for invalid ids: wrong for a POST body id; 400 is uniform.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing regression tests | `src/tests/test_definition_store_containment.py` | AC1 | 27 fail on current code |
| T2 | `InvalidEntityIdError`, `_check_ids`, guards in the five operations, string-path atomic helpers | `src/definitions/base.py`, `store.py`, `db_store.py` | AC1, AC2 | store tests |
| T3 | App-level 400 handler | `src/api/main.py` | AC1 | route tests |
| T4 | PR CodeQL check, then re-query alerts 11-23 after the master scan | n/a | AC2 | `gh api .../alerts/<id>` |

## Data, API and migration impact

None for data. An invalid id now returns 400 instead of 500. Unknown entity type raises instead of being accepted.

## Security and failure modes

Containment on every file operation; unknown entity types and symlinks leaving the store are refused. Failure: 400 with the invalid-id
message.

## Rollout and rollback

Merge, wait for CodeQL on master. Rollback: revert the merge commit.

## Risks and open points

CodeQL may track taint into the atomic helpers; the PR CodeQL result check shows it before merge, and the guard shape can be iterated
(for example inlining the helper bodies).
