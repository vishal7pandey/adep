# ADE-74 — Test plan: Bootstrap secret clear-text

Status: draft · Risk: high · Jira: ADE-74

Test framework: pytest via `uv run python -m pytest`; command for all: `uv run python -m pytest src/tests -q -m "not integration"`
(baseline: 2 known failures, ADE-23 and ADE-24). Tests in `src/tests/test_auth.py`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | `src/tests/test_auth.py::TestBootstrap::test_bootstrap_secret_not_sent_through_print`, plus existing `test_bootstrap_secret_printed_to_stdout`, `test_bootstrap_secret_never_logged` | secret and key id appear on stdout once, returned secret equals the one shown | banner is flushed (stdout captured fully) | `print` patched to a recorder: never called with the secret; caplog has no record containing the secret | verified |
| AC2 | manual | n/a (scanner re-query) | alert 46 `fixed` on master; PR CodeQL check green | n/a: single state read | still `open`: ticket stays open, dismissal proposal, never dismiss | planned |

## Regression risk

`test_bootstrap_creates_key`, `test_bootstrap_raises_if_keys_exist` and the middleware tests that bootstrap a key must stay green.

## Untestable AC

AC2 is a scanner state, not testable in the suite.

## Manual checks

AC2: `gh api repos/vishal7pandey/adep/code-scanning/alerts/46`, read `state`.

## Audit (after implementation)

AC1: `src/tests/test_auth.py::TestBootstrap::test_bootstrap_secret_not_sent_through_print` (new) plus the two existing bootstrap tests. Mutation: with the original `print(..., flush=True)` restored, the new test fails (`any(secret in text for text in printed)` true); with the fix it passes. 5 bootstrap tests pass.

Full suite `uv run python -m pytest src/tests -q -m "not integration"` in the shared main-checkout venv: 12 failed, 2024 passed on the branch; the same 12 fail on unmodified master in this venv (the 2 known ADE-23/ADE-24 plus 10 environment failures: 6 e2e, 3 paddleocr contract, 1 stabilization, all deselected in CI), so no regression. `ruff format --check` clean on the two touched files.

AC2: NOT met (2026-10-07): after the master CodeQL run alert 46 is `fixed`, but CodeQL raised a successor alert 52 (py/clear-text-logging-sensitive-data, src/api/auth.py:375, the `sys.stdout.write` of the one-time banner); the PR CodeQL check had been green, so the PR check does not catch a relocated alert. ADE-74 stays open; a dismissal proposal (won't fix, intended one-time console display) is on the Jira issue for the owner. The status below stays `planned`.
