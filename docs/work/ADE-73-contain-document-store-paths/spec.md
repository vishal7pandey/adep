# ADE-73 — Contain document store paths (CodeQL py/path-injection, 6 alerts)

Status: draft · Risk: high · Jira: ADE-73
<!-- Security finding: neutral wording on purpose; this repo is public. -->

Grouped code-scanning findings of rule `py/path-injection` (high), repo vishal7pandey/adep, ref master. Alerts: 24, 25, 26, 27
in `src/documents/store.py` (lines 313, 315, 321, 328), 7 at `src/api/routes/documents.py:138` (thumbnail route) and 10 at
`src/api/routes/runs.py:154` (run-creation document guard). Note: the Jira ticket text lists 7 as runs.py and 10 as documents.py;
the alerts API says the opposite (7 = documents.py:138, 10 = runs.py:154). Both are covered either way.

## Repro

Environment: `master` @ dbd3c28.

An id from the URL (or from an LLM tool argument) flows into `self.docs_dir / doc_id / ...` and into `exists()` / `read_text()`,
and the request `document_url` flows into `Path(...).resolve()`. The id is checked by a regex (`get_doc_dir`) which CodeQL does
not recognise as a sanitizer, and a symlink inside `documents/` can still lead out of the store.

Automated repro (failing on current code), `uv run python -m pytest src/tests/test_document_store_containment.py -q`:

- `TestDocumentRoutes::test_get_document_invalid_id_is_404`, `::test_thumbnail_invalid_id_is_404`,
  `::test_suggest_agent_invalid_id_is_404`: an invalid id raises an unhandled `ValueError` (HTTP 500) instead of 404.
- `TestDocumentRoutes::test_thumbnail_outside_the_store_is_not_served`: the thumbnail route has no containment check.
- `TestEngineCallers::test_page_image_path_for_invalid_id_is_none`: an LLM tool call with a bad id raises `ValueError`.
- `TestRunCreationDocumentRoots::test_auto_route_with_a_file_path_is_a_clean_4xx`: `definition_id=auto` with a file path
  as `document_url` raises `ValueError` from `get_document` (500) instead of reaching the file-path branch (400).

Honest note: the traversal ids themselves are already rejected by the regex, and the run-creation guard already refuses
sibling-prefix paths; those tests pass before and after and pin the behaviour. Two symlink tests skip on accounts that may not
create symlinks.

Reproducibility: always (CodeQL reports the six alerts on every analysis; the 500s are deterministic).

## Expected

Every document store operation touches a file only inside the true branch of an inline
`startswith(realpath(docs_dir) + os.sep)` guard on the `os.path.realpath` of the candidate; an invalid or escaping id raises
`ValueError`, which every caller turns into a clean 4xx (routes: 404) or a tool "not found" result; legitimate ids behave as before.
The run-creation guard uses the same shape with one literal root per check.

## Actual

Containment is by regex only (not modelled by the analyzer) and `ValueError` escapes from three routes, the auto-route branch of
`POST /runs` and two engine callers as HTTP 500 or a tool crash.

## Root cause (with evidence)

- Where: `src/documents/store.py:310-330`, `src/api/routes/documents.py:97-143`, `src/api/routes/runs.py:117-127,153-156`,
  `src/engine/tools.py:86`, `src/engine/agent.py:171-178`.
- Why: path built from a request value and used with no recognised guard; callers written for `FileNotFoundError` only.
- Introduced by: BLK-059 and later; `get_page` was hardened in ADE-54, the others were not.
- Evidence: alerts 7, 10, 24-27 state `open`; the failing tests above.

## Blast radius

Callers of `get_document` / `get_page_path` / `get_thumbnail_path`: documents routes, `runs.py` auto-route, `run_engine.py` (already
catches `ValueError`), `engine/tools.py`, `engine/agent.py`. `import_document` builds ids itself (`uuid`), unchanged.

## Regression criterion (AC1)

AC1: The failing tests listed under Repro pass after the fix; the containment, sibling-prefix and legitimate-id tests in
`src/tests/test_document_store_containment.py` and the existing `test_path_containment.py`, `test_async_runs.py` tests stay green.

AC2: After the merge and the push scan, alerts 7, 10, 24, 25, 26 and 27 each re-query as `fixed` on master, and the PR CodeQL
result check shows no new alert. Any alert that stays open after a demonstrably safe fix gets a dismissal proposal on ADE-73, never
a dismissal by the agent.

## Fix constraints

- `os.path.realpath` on the base and the candidate, then ONE inline `startswith(base + os.sep)` guard whose true branch holds the file
  operation; no helper that returns a checked string, no `Path.resolve()` / `parents` forms.
- Store keeps raising `ValueError` for invalid ids (existing contract) and `FileNotFoundError` for unknown documents.
- Minimal diff: store, the two routes, and the `ValueError` handling in the callers listed above.

## Risks

Risk high (path handling). A symlinked document dir that previously worked now fails (intended). Windows case differences are handled by
using `realpath` on both sides. Rollback: revert the merge commit.
