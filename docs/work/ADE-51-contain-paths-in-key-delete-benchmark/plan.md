# ADE-51 — Contain paths in key delete, benchmark fixture dir and page file (CodeQL path-injection alerts 3, 4, 5, 6)

Status: draft · Risk: high · Jira: ADE-51
Created: 2026-10-06 · Slug: contain-paths-in-key-delete-benchmark · Spec: spec.md

## Summary

Resolve each user-influenced path with `os.path.realpath`, require it to stay under the resolved base directory with a
`startswith(base + os.sep)` check written inline at the point of use (the pattern that closed the equivalent chatpid alerts), and
map a refusal to the route's existing error. Three call sites, no shared helper, so each sanitizer stays visible to CodeQL.

**Size:** S

## Current state

- `src/api/auth.py` `ApiKeyStore.delete` (lines 296-302): `path = self._path_for(key_id)`, then `path.exists()` and `path.unlink()`.
  `delete_key` in `src/api/routes/keys.py` maps `FileNotFoundError` to 404.
- `src/api/routes/benchmarks.py` `trigger_benchmark` (lines 52-62): `Path(req.fixture_dir)`, relative paths joined to `Path.cwd()`,
  then `exists()`; missing gives 404 `Fixture directory not found`; provider names are validated after the path.
- `src/api/routes/documents.py` `get_page` (lines 105-117): `store.get_page_path(...)` then `FileResponse(str(page_path))`; only
  `FileNotFoundError` is caught.
- Tests: `uv run python -m pytest src/tests -q -m "not integration"`; baseline 2 failures (ADE-23, ADE-24). Lint:
  `uv run ruff check <files>` and `uv run ruff format --check <files>`.
- The failing regression tests already exist in `src/tests/test_path_containment.py` (7 of 13 fail).

## Approach

1. `auth.py` `delete`: compute `base = os.path.realpath(self.base_dir)` and
   `path = os.path.realpath(os.path.join(base, f"{key_id}.json"))`; if `not path.startswith(base + os.sep)` raise
   `FileNotFoundError` (route turns it into 404); then `os.path.exists(path)` / `os.unlink(path)` on the checked string.
2. `benchmarks.py` `trigger_benchmark`: validate provider names first (so an invalid provider is a 400 whatever the directory),
   then `base = os.path.realpath(os.getcwd())`, `fixture_dir = os.path.realpath(os.path.join(base, req.fixture_dir))` (an
   absolute `fixture_dir` replaces the base in `os.path.join`, and is then checked like any other); if it is not under
   `base + os.sep` (so the working directory itself is refused too; a compound "equal to base or under base" condition was
   not recognised by CodeQL on PR #21, alert 47, and benchmarking the whole working directory is not a use case) raise the existing 404 with the user-supplied value in the message; continue with the
   checked string.
3. `documents.py` `get_page`: also catch `ValueError` (invalid id) as 404; resolve `docs_root = os.path.realpath(store.docs_dir)` and
   `page_file = os.path.realpath(page_path)`; if not under `docs_root + os.sep` raise the same 404; `FileResponse(page_file)`.

**Alternatives rejected**
- A shared `safe_join` helper in a new module: CodeQL can lose the barrier across a function boundary, and the task wants the
  sanitizer visible at each call site. Revisit only if CodeQL keeps an alert open.
- `Path.resolve()` + `is_relative_to`: valid, but the `os.path` form is the one verified to close the chatpid alerts.
- A regex check on key ids: does not satisfy CodeQL and is weaker than containment.
- Returning 400 for an out-of-base benchmark directory: breaks the existing contract that a bad directory is a 404 and tells the
  caller the path exists elsewhere.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Contain `ApiKeyStore.delete` | `src/api/auth.py` | AC1, AC2 | `uv run python -m pytest src/tests/test_path_containment.py src/tests/test_auth.py -q` passes |
| T2 | Contain `trigger_benchmark` (providers first) | `src/api/routes/benchmarks.py` | AC1, AC2 | same file plus `src/tests/test_benchmark_suite.py` passes |
| T3 | Contain `get_page`, map invalid id to 404 | `src/api/routes/documents.py` | AC1, AC2 | same file passes |
| T4 | Full backend suite, ruff check and format on touched files, mutation audit | none | AC1, AC2 | `-m "not integration"`: only ADE-23 and ADE-24 fail; ruff clean on touched files |
| T5 | After merge and CodeQL re-analysis, re-query alerts 3, 4, 5, 6 | none (Jira comments) | AC3 | `gh api repos/vishal7pandey/adep/code-scanning/alerts/<id>` shows `fixed` |

## Data, API and migration impact

None for data. Behaviour: out-of-directory inputs now answer the normal 404 (key delete, benchmarks, page) instead of acting on
the path; an invalid document id on the page route is 404 instead of 500. No schema, config or env changes.

## Security and failure modes

Removes four high path-injection findings. Failure modes: a legitimate fixture directory outside the working directory is now
refused (404); symlinks inside a base that point outside are refused because `realpath` follows them (intended). No secrets are involved.

## Rollout and rollback

Merge the PR; CI runs the backend suite and CodeQL. Rollback: revert the merge commit (the alerts reopen).

## Risks and open points

- CodeQL may not close an alert if its sanitizer matching differs for one site; the signal is the alert state after the post-merge
  analysis. The response is to improve the fix, not to dismiss.
- The CodeQL run for `master` may take a while after the merge; tickets stay open until each alert reads `fixed`.
