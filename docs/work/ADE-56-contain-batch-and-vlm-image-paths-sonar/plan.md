# ADE-56 — Contain batch and VLM image paths (Sonar S2083 ADE-56, ADE-57)

Status: draft · Risk: high · Jira: ADE-56
Created: 2026-10-06 · Slug: contain-batch-and-vlm-image-paths-sonar · Spec: spec.md

## Summary

Resolve each externally influenced path with `os.path.realpath`, require it to stay under an allowed root with a direct
`startswith(root + os.sep)` condition written inline at the point of use, and refuse otherwise. Keep the VLM's working-directory
and temp-directory checks as two named operands in one explicit boolean condition; do not hide them in a collection, generator,
or helper, because CodeQL did not recognize those forms as guarding the sink.

**Size:** S

## Current state

- `src/api/routes/batches.py` `_batch_path` (line 46) joins `Path.cwd()/.adep/batches` and `f"{batch_id}.json"`; `save_batch`
  (line 50) does `path.write_text(json.dumps(...))`. `cancel_batch` passes the URL's `batch_id` to `load_batch` then `save_batch`.
- `src/providers/vlm_azure.py` `_encode_image` (line 58) does `open(image_path, "rb")`; `_call_vlm` (line 72) is wrapped in
  `tenacity.retry(stop_after_attempt(3), wait_exponential(min=2), retry_error_callback=lambda ...: None)`, so any exception is
  retried three times and then turned into `None` ("VLM call failed after retries").
- Tests: `uv run python -m pytest src/tests -q -m "not integration"`; baseline 2 failures (ADE-23, ADE-24). Lint:
  `uv run ruff check <files>` and `uv run ruff format --check <files>`.
- The failing regression tests exist in `src/tests/test_sonar_path_containment.py` (7 of 14 fail).

## Approach

1. `save_batch`: `base = os.path.realpath(os.path.join(os.getcwd(), ".adep", "batches"))` (same directory `_batches_dir()`
   creates, which is still called first so it exists), `path = os.path.realpath(os.path.join(base, f"{batch_id}.json"))`; if
   `not path.startswith(base + os.sep)` raise `ValueError`; then `open(path, "w", encoding="utf-8")` on the checked string.
2. `_encode_image`: name `working_root = os.path.realpath(os.getcwd())` and `temp_root = os.path.realpath(tempfile.gettempdir())`;
  resolve `real_path = os.path.realpath(image_path)`; then use an explicit check equivalent to
  `if not (real_path.startswith(working_root + os.sep) or real_path.startswith(temp_root + os.sep)): raise ImagePathNotAllowed(...)`.
  Keep the checked `real_path` as the argument to `open(real_path, "rb")`. Do not wrap roots in `any(...)`, a generator, or a
  shared helper. The MIME type is still taken from the extension.
3. `_call_vlm`: add `retry=retry_if_not_exception_type(ImagePathNotAllowed)` so a refusal is raised at once instead of
   waiting through three backoff rounds; `vlm()` already turns an exception into `ToolResult(ok=False, ...)`, and `classify.py`
   catches `Exception` around its calls.

**Alternatives rejected**
- A shared `safe_join` helper in a new module: the scanner can lose the sanitizer across a function boundary, and the task wants
  it visible at each sink. Revisit only if SonarCloud keeps an issue open.
- Allowing only `.adep/documents`: the engine also reads `sample-data/` fixtures, and writes crops and survey images to the system
  temp directory (`tempfile.mkstemp`), so both the working tree and the temp directory are needed.
- A suffix allow-list for images: a separate hardening (the working tree also holds `.env`); out of scope for these two findings,
  noted in notes.md for the later sweep.
- Catching the refusal inside `_call_vlm` and returning `None`: hides the reason; the exception carries the message into
  `ToolResult.error`.
- A generator or shared containment helper for the two VLM roots: CodeQL continued to report the tainted path at `realpath` or
  `open`; use the same direct conditional pattern already present in `src/api/routes/documents.py` instead.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Contain `save_batch` | `src/api/routes/batches.py` | AC1, AC2 | `uv run python -m pytest src/tests/test_sonar_path_containment.py src/tests/test_batches.py -q` passes |
| T2 | Contain `_encode_image` with explicit root checks; do not retry the refusal | `src/providers/vlm_azure.py` | AC1, AC2, AC4 | containment and VLM caller tests pass; PR CodeQL check reports no new alert 50 |
| T3 | Full backend suite, ruff check and format on touched files, mutation audit | none | AC1, AC2 | `-m "not integration"`: only ADE-23 and ADE-24 fail; ruff no worse on touched files |
| T4 | After merge and the push scan, re-query Sonar and CodeQL | none (Jira comments) | AC3, AC4 | both Sonar issues are closed and CodeQL alert 50 is `fixed` |

## Data, API and migration impact

None for data. Behaviour: a batch id that escapes `.adep/batches` raises `ValueError` in `save_batch` (the cancel route would answer
500 for such an id only when a file outside the directory could be loaded first, which `load_batch` still allows: separate finding);
an image path outside the working tree and the temp directory now yields `ok=False` from `vlm`/`read_*` tools. No schema, config
or env changes.

## Security and failure modes

Removes two BLOCKER path-traversal findings. Failure modes: legitimate image outside the allowed roots is refused with the
message "Image path is outside the allowed directories"; symlinks inside a root that point outside are refused because `realpath`
follows them (intended); on Windows a differing drive-letter case is handled by `realpath`. No secrets are involved.

## Rollout and rollback

Merge the PR; CI runs the backend suite and the SonarCloud scan. Rollback: revert the merge commit (the issues reopen).

## Risks and open points

- SonarCloud may not treat the inline check as a sanitizer for one site; the signal is the issue state after the PR scan and the
  post-merge push scan. The response is to improve the fix, not to dismiss.
- A real workflow that points a tool at an image outside the repo would now fail; none found in `src/` or the tests.
