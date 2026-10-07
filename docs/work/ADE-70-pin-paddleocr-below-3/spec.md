# ADE-70 — Pin paddleocr below 3

Status: draft · Risk: medium · Jira: ADE-70

## Repro

Environment: `master` @ d13c1e9 (locked `paddleocr` 3.7.0, from Dependabot PR #28), Windows, Python 3.14 venv.

1. Install the locked environment (`uv sync --frozen --all-extras`).
2. Run the exact call of `src/providers/ocr_paddle.py:30`:
   `PaddleOCR(use_angle_cls=True, lang="en", show_log=False)`.

Observed on 2026-10-07 with the installed 3.7.0: `ValueError: Unknown argument: show_log` (plus a deprecation warning that
`use_angle_cls` is replaced by `use_textline_orientation`). The signature of 3.x `PaddleOCR.__init__` lists named
parameters only (`lang`, `ocr_version`, `use_textline_orientation`, ...) plus `**kwargs`, and `show_log` is not among them.

Automated repro: `src/tests/test_paddleocr_contract.py` (new) constructs the real class with the provider's arguments
without touching the model files; it fails on a 3.x resolution and passes on 2.x. The existing provider tests mock the
engine, which is why CI stayed green.

Reproducibility: always.

## Expected

The primary OCR backend returns text and boxes, as it did on 2.10.0 (the version in use before PR #28).

## Actual

`detect_layout` catches the `ValueError` in its broad `except Exception` and returns
`ok=False, error="PaddleOCR layout failed: Unknown argument: show_log"` for every image. The call
`engine.ocr(image_path, cls=True)` and the nested-list parsing (`result[0]`, `[bbox, (text, confidence)]`) are also the 2.x
shapes; 3.x `ocr()` wraps `predict()` and returns result objects.

## Root cause (with evidence)

- Where: `pyproject.toml:30` (`paddleocr>=3.7.0`) against `src/providers/ocr_paddle.py:30,50,57-61`.
- Why it fails: a major version bump (2.10.0 to 3.7.0, Dependabot PR #28, merged 2026-10-06 with green checks) changed the
  constructor arguments and the result type; the provider still speaks the 2.x API and no test runs the real engine.
- Introduced by: commit 71e2fc4 (merge cfab8c0), `chore(deps): bump paddleocr from 2.10.0 to 3.7.0`.
- Evidence: the `ValueError` above, reproduced against the installed 3.7.0; `git show 6b93866:uv.lock` shows `paddleocr`
  2.10.0 locked before the bump.

## Blast radius

`src/providers/ocr_paddle.py` (`detect_layout`, `detect_text`, `ocr`) and everything that calls those tools. OCR through
PaddleOCR fails in any environment built from the locked versions (since the merge on 2026-10-06; no release was cut).
The engine that uses it is slated for retirement (ADE-33), so migrating the provider to the 3.x API is not worth doing now.
No data was processed wrongly: the tools return `ok=False`.

## Regression criterion (AC1)

AC1: A guard test fails when the resolved `paddleocr` (installed package and `uv.lock`) is 3.x or newer, and passes on
2.x; and a non-mocked contract test checks the installed `PaddleOCR` class against what the provider relies on. Both fail
on the current master (3.7.0) and pass after the fix.

AC2: `pyproject.toml` requires `paddleocr>=2.7,<3`, `uv.lock` resolves `paddleocr` to 2.10.0 (the version before PR #28),
and `uv sync --frozen --all-extras` works.

AC3: `.github/dependabot.yml` ignores major updates of `paddleocr` for the `uv` ecosystem, with a comment pointing to
ADE-70 and ADE-33. Nothing else in that file changes.

## Fix constraints

Smallest correct fix: restore the working major; no provider code change. Do not edit the Dependabot branch (it is merged).
The pin is lifted only by a deliberate migration of the provider (or its retirement under ADE-33).

## Risks

Medium: touches the lockfile, which re-resolves unrelated packages unless `uv lock` is kept minimal (check the lockfile
diff; the dependencies of paddleocr 2.x differ from 3.x so some removals are expected). Rollback: revert the merge commit.
2.10.0 is old and may carry its own advisories; none is open as a Dependabot alert on this repo at the time of writing.
