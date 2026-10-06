# ADE-51 — Contain paths in key delete, benchmark fixture dir and page file (CodeQL path-injection alerts 3, 4, 5, 6)

Status: draft · Risk: high · Jira: ADE-51
<!-- Security finding: neutral wording on purpose; this repo is public. -->

Covers four Jira findings, one CodeQL rule (`py/path-injection`, high): ADE-51 (code-scanning alert 3, `src/api/auth.py:299`),
ADE-52 (alert 4, `src/api/auth.py:301`), ADE-53 (alert 5, `src/api/routes/benchmarks.py:60`), ADE-54 (alert 6,
`src/api/routes/documents.py:115`). ADE-51 is the key of this work item; the other three tickets close separately, each on its
own re-queried alert. Only these four alerts are in scope; the other path-injection alerts belong to a later sweep.

## Repro

Environment / version / commit where it fails: `master` @ 34e06ef, Python 3.14 venv, Windows; the logic is platform independent
except where noted.

Automated repro (failing tests, with the command to run them):

- `src/tests/test_path_containment.py`, run `uv run python -m pytest src/tests/test_path_containment.py -q`.
  On current code 7 of 13 tests fail (the other 6 pin legitimate behaviour and pass):
  - `TestApiKeyDeleteContainment::test_delete_rejects_relative_traversal_and_keeps_outside_file` and
    `::test_delete_rejects_absolute_key_id_and_keeps_outside_file`: `ApiKeyStore.delete` does not raise `FileNotFoundError`
    and removes a file outside `api_keys/` (DID NOT RAISE).
  - `::test_delete_route_returns_404_for_traversal_id`: `DELETE /admin/keys/<id>` answers 204 instead of 404 on Windows
    (where a backslash is a path separator in a single URL segment).
  - `TestBenchmarkFixtureDirContainment::test_relative_traversal_outside_cwd_is_rejected` and
    `::test_absolute_path_outside_cwd_is_rejected`: `POST /admin/benchmarks` answers 200 and runs the suite on a directory
    outside the working directory (expected 404).
  - `TestDocumentPageContainment::test_invalid_document_id_is_404_not_a_server_error`: an invalid document id raises an
    unhandled `ValueError` (500) instead of the normal 404.
  - `::test_page_file_outside_the_document_store_is_not_served`: the page route serves any file path the store hands back,
    even outside the document store (200 instead of 404).

Reproducibility: always.

## Expected

Each of the four code paths only touches files inside its intended directory, and a value that points elsewhere is refused with
the project's normal error: key delete raises `FileNotFoundError` (route: 404, as for an unknown key), the benchmark route
answers 404 "Fixture directory not found" (the same answer as for a missing directory), the page route answers 404. Legitimate
inputs behave as before.

## Actual

- `ApiKeyStore.delete(key_id)` builds `base_dir / f"{key_id}.json"` from the URL segment and calls `exists()` and `unlink()`
  on it with no containment check, so a crafted id can delete a `.json` file outside `.adep/api_keys/`.
- `trigger_benchmark` builds a `Path` from the request body `fixture_dir` (absolute paths accepted as is) and probes it with
  `exists()`, then runs the suite on it, so any directory on the server can be probed and benchmarked.
- `get_page` hands the path returned by the store straight to `FileResponse`; the store validates the document id with a
  regex, but the route does not check the final path, and an invalid id escapes as an unhandled `ValueError`.

## Root cause (with evidence)

- Where: `src/api/auth.py:296-302` (`ApiKeyStore.delete`, `_path_for` at `:233`), `src/api/routes/benchmarks.py:55-62`
  (`trigger_benchmark`), `src/api/routes/documents.py:105-117` (`get_page`, store side `src/documents/store.py:124-134,317-323`).
- Why it fails: user-controlled text is joined into a filesystem path and used without first resolving it
  (`os.path.realpath`) and proving it stays under the intended base directory. Validation that exists elsewhere (the document id
  regex) is not applied where the file is used, and a bad id is not mapped to the normal error.
- Introduced by: always present (original implementations).
- Evidence: the 7 failing tests above; CodeQL alerts 3 to 6 report "This path depends on a user-provided value".

## Blast radius

- Other callers of the same code: `ApiKeyStore.update` and `create` also use `_path_for`, but their key id comes from a key
  already loaded from the store (not from the URL), so they are not reachable with a crafted id; left unchanged. The key routes
  `PUT /admin/keys/{key_id}` and `POST .../rotate` look the key up with `get()` (which compares ids in memory) before any file
  access.
- Sibling code with the same pattern and NOT in scope (separate alerts / later sweep): `get_thumbnail` and `get_document`
  in `documents.py` (same unhandled `ValueError` for an invalid id), and about 40 other path-injection alerts.
- Exposure: the key route needs an admin credential when auth is on (`ADE_AUTH_ENABLED`), and is open when auth is off (local
  dev default). The benchmark route is under `/admin`. Data already affected: none known; `.json` files outside the key
  directory could have been deleted, which the key directory listing would not show.
- Since: first commits of these modules.

## Regression criterion (AC1)

AC1: The failing tests in `src/tests/test_path_containment.py` pass after the fix and fail on the current code: for each of
`ApiKeyStore.delete`, `POST /admin/benchmarks` and `GET /documents/{id}/page/{n}`, an input that escapes the intended directory
is refused with the normal error and no file outside the directory is touched, deleted, served or benchmarked.

AC2: Legitimate behaviour is unchanged: deleting an existing key and an unknown key, a fixture directory inside the working
directory (relative or absolute) and a missing one, and serving a real page and a missing page keep their current results; the
rest of the backend suite stays at its known baseline (`-m "not integration"`: only ADE-23 and ADE-24 fail).

AC3: After the fix is merged and CodeQL has re-analysed `master`, `gh api repos/vishal7pandey/adep/code-scanning/alerts/<id>`
returns `state: fixed` for ids 3, 4, 5 and 6 (verified after merge; the Jira tickets close only on that).

## Fix constraints

- Containment is checked inline at each point of use with the pattern CodeQL recognises: `os.path.realpath` on the base and on
  the candidate, then `candidate.startswith(base + os.sep)`, before any `exists()`, `unlink()`, `FileResponse` or suite run.
- Minimal diff: only `src/api/auth.py` (`delete`), `src/api/routes/benchmarks.py` (`trigger_benchmark`),
  `src/api/routes/documents.py` (`get_page`) and the new test file, plus this work item folder. No API shape change.
- The benchmark base directory is the working directory (the directory itself is refused too, only subdirectories are allowed), matching how relative `fixture_dir` values are already resolved.
  Out-of-base values get the same 404 as a missing directory (no filesystem probing, no existence oracle).
- Do not touch the other path-injection alerts or unrelated files.

## Risks

- Risk high because it is a security fix on admin and file-serving routes. A legitimate fixture directory outside the working
  directory (for example an absolute path elsewhere on disk) will now be refused: documented behaviour change; the demo set
  `sample-data/` is inside the repo. Rollback: revert the commit.
- If CodeQL does not recognise the inline check, the alert stays open; then the fix is improved (not dismissed) and the ticket
  stays open meanwhile.
