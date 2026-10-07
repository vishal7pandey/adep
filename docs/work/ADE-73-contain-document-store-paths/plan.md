# ADE-73 — Contain document store paths

Status: draft · Risk: high · Jira: ADE-73
Created: 2026-10-07 · Slug: contain-document-store-paths · Spec: spec.md

## Summary

Add inline realpath + `startswith(base + os.sep)` containment to the three `DocumentStore` reads, the thumbnail route and the
run-creation document guard, and make every caller treat `ValueError` (invalid id) like "not found".

**Size:** S

## Current state

`src/documents/store.py` `get_document`, `get_page_path`, `get_thumbnail_path` build `docs_dir / doc_id / name` after a regex check in
`get_doc_dir`. `documents.py` get_page already has a guard (ADE-54). Tests: `src/tests/test_path_containment.py`,
`test_async_runs.py`. Run: `uv run python -m pytest src/tests -q -m "not integration"`.

## Approach

Per operation: validate the id (`get_doc_dir`), `base = os.path.realpath(self.docs_dir)`, `target = os.path.realpath(os.path.join(base,
doc_id, name))`, `if target.startswith(base + os.sep):` do the file operation, else `raise ValueError`. Routes: catch
`(FileNotFoundError, ValueError)` and answer 404; thumbnail route serves inside its own guard like `get_page`. `runs.py`: realpath of
the document path and each root, one `startswith` per root. Engine callers catch `ValueError`.

**Alternatives rejected**
- A shared helper returning a checked path: the analyzer may not see the guard at the sink (lesson from ADE-51 to ADE-57).
- Raising `FileNotFoundError` for a bad id: would hide the invalid-id case from existing callers that already catch `ValueError`.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing regression tests | `src/tests/test_document_store_containment.py` | AC1 | 12 fail on current code |
| T2 | Containment in the store reads | `src/documents/store.py` | AC1, AC2 | store tests |
| T3 | Routes: 404 on `ValueError`, thumbnail guard, run-creation guard, auto-route fallback | `src/api/routes/documents.py`, `runs.py` | AC1, AC2 | route tests |
| T4 | Engine callers catch `ValueError` | `src/engine/tools.py`, `src/engine/agent.py` | AC1 | caller test |
| T5 | PR CodeQL check, then re-query alerts after master scan | n/a | AC2 | `gh api .../alerts/<id>` |

## Data, API and migration impact

None. Invalid ids now return 404 instead of 500.

## Security and failure modes

Containment on every read from a request-derived id; symlinks leaving the store are refused. Failure: invalid id -> 404 / tool "not found".

## Rollout and rollback

Merge, wait for CodeQL on master. Rollback: revert the merge commit.

## Risks and open points

CodeQL may need a second iteration of the guard shape; the PR CodeQL result check shows it before merge.
