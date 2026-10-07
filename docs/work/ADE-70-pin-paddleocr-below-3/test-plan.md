# ADE-70 — Test plan: Pin paddleocr below 3

Status: draft · Risk: medium · Jira: ADE-70

Test framework and conventions found: pytest, tests in `src/tests/`, run with `uv run python -m pytest`. Command for all:
`uv run python -m pytest src/tests -q -m "not integration"` (baseline: 2 known failures, ADE-23 and ADE-24).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | `src/tests/test_paddleocr_contract.py::TestVersionGuard` (installed version, `uv.lock`, `pyproject.toml` cap, two helper tests) | installed 2.10.0, lock 2.10.0, pin `>=2.7,<3` pass | major 10 is not 2; lock entry with CRLF read | on the 3.7.0 resolution the three file/installed tests fail (3 failed) | verified |
| AC1 | unit (not mocked) | `src/tests/test_paddleocr_contract.py::TestProviderMatchesInstalledPackage` (provider kwargs vs the installed package's own option and `ocr()` definitions) | `use_angle_cls`, `lang`, `show_log` and `ocr(cls=)` found in 2.10.0 | provider kwargs pinned to the known set, so a migration forces the contract to be updated | on 3.7.0: `show_log`, `lang`, `use_angle_cls` not defined, `ocr()` has no `cls` (2 failed) | verified |
| AC2 | integration | `uv lock --check`, `uv sync --frozen --all-extras`, full suite | lock consistent, sync works, installed 2.10.0 | only `paddleocr` changed version in the lock; 29 removed, 21 added transitive packages | n/a | verified |
| AC3 | manual | n/a (config) | `.github/dependabot.yml` parses, ignore block under the `uv` ecosystem, diff is that block only | n/a | n/a | verified |

## Regression risk

Provider tests (`test_audit_fixes.py` and others) mock the engine and are unaffected. The lockfile drops and adds transitive
packages (3.x and 2.x have different dependency sets): the full suite covers the rest.

## Untestable AC

The 2.x constructor is not called for real: `import paddleocr` needs `paddle` (paddlepaddle, not a project dependency) and
construction downloads model files. The contract test therefore reads the installed package's own option definitions (static,
no import, no network). Observation for the owner: because paddlepaddle is not declared, a locked environment has the provider
answer "PaddleOCR is not installed" on 2.x; that is pre-existing and out of scope here (ADE-33 retires the engine).

## Manual checks

AC3: read the diff of `.github/dependabot.yml`; after merge Dependabot's next run must not propose paddleocr 3.

## Audit (after implementation)

AC1, `src/tests/test_paddleocr_contract.py` (8 tests). Red on the old state: run against the 3.7.0 environment with the
old `pyproject.toml` and `uv.lock`, 5 failed and 3 passed (installed version, lockfile, pyproject cap, constructor options
`['lang', 'show_log', 'use_angle_cls']` not defined, `ocr()` has no `cls`). Green on the fix (paddleocr 2.10.0): 8 passed.
Mutation checks (each restored):

- Mutation 1, `paddleocr>=2.7,<3` changed to `paddleocr>=2.7` in `pyproject.toml`: `test_pyproject_caps_paddleocr_below_3` failed (1).
- Mutation 2, an extra keyword `bogus_flag=1` added to `PaddleOCR(...)` in the provider: `test_provider_arguments_are_what_the_helper_expects`
  and `test_constructor_options_are_accepted_by_the_installed_package` failed (2).
- Mutation 3, an extra keyword added to `engine.ocr(...)`: the pinned-arguments test and `test_ocr_method_takes_the_keywords_the_provider_passes` failed (2).

AC2: `uv lock --check` consistent (230 packages); `uv sync --frozen --all-extras` ok, installed paddleocr 2.10.0. Only `paddleocr`
changed version among packages present in both locks (3.7.0 to 2.10.0).

Full suite `uv run python -m pytest src/tests -q -m "not integration"` in the clean worktree (no `.env`): 2000 passed, 2 skipped,
19 deselected, 9 failed = the 2 known baseline failures (ADE-23, ADE-24) plus the 7 clean-checkout failures CI deselects;
with those 7 deselected only ADE-24 remains (1998 passed). No failure involves the new tests.

AC3: diff of `.github/dependabot.yml` is the `ignore` block under the `uv` ecosystem (dependency `paddleocr`, `version-update:semver-major`).
