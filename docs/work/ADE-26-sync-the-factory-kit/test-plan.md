# ADE-26 — Test plan: Sync the factory kit

Status: draft · Risk: low · Jira: ADE-26

Test framework and conventions found: a sync is a mechanical configuration change with no new code, so the checks
are the factory's own gates plus the project's existing suite: `factory sync --check`, `.factory/verify.py`,
`factory doctor`, CI on the pull request, and `uv run python -m pytest src/tests -q -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `factory sync .` then `factory sync --check .` | sync: 5 created, 14 updated, check exit 0 | n/a: idempotence is shown by running `--check` twice, second run unchanged | n/a: covered by AC2 | verified |
| AC2 | integration | edit `.claude/skills/factory-spec/SKILL.md` locally, run `factory sync --check .` | n/a: covered by AC1 | one-line change in one managed file | check reports the file and exits non-zero; after restore exits 0 | verified |
| AC3 | integration | `python .factory/verify.py` | exit 0 on the branch | the 17 status changes and the new item `draft` to `in-review` | n/a: the verify rules are the factory's, a failing item would show as an error line | verified |
| AC4 | manual | `git diff .github/workflows/ci.yml` | only `uses:` lines change, to checkout v7, setup-uv v10.2.0, setup-node v7, paths-filter v4 | comment blocks and `--deselect` lines identical | n/a: a removed disabled-step comment would show as a removed line in the diff | verified |
| AC5 | integration | PR check `sonar` | job green, log prints the skipping notice | n/a: only the dormant state is reachable without the owner's key and token | n/a: no secret exists to leak; the file holds placeholders | verified |
| AC6 | integration | `grep -E "^(status\|pr):" docs/work/*/item.yaml` plus `gh pr view <n> --json state` | all 17 `merged`, `pr` string | ADE-30 (`spec-approved`) untouched | no `merged` item with `pr: null` | verified |
| AC7 | integration | `uv run python -m pytest src/tests -q -m "not integration"` | only `test_compact_run_not_in_executor_returns_false` and `test_seeded_definitions_exist` fail | n/a: no code changed | n/a: a third failure would be a regression | verified |
| AC8 | integration | `gh pr checks --watch` | verify, backend, frontend, docker-build, sonar, CodeQL green | n/a | n/a: a red check blocks the merge | verified |

## Regression risk

The only behaviour that can change is CI: newer action majors (`setup-uv` v3 to v10.2.0 above all) and the new
`verify.py`. The backend, frontend and docker-build jobs on the PR are the regression test. Application tests do
not change; the baseline of 2 known failures must hold.

## Untestable AC

None. AC5 can only be shown in the dormant state; the configured state needs the owner's key and token and is the
factory's own tested template.

## Manual checks

AC4: read the `ci.yml` diff and confirm that only `uses:` lines changed.

## Audit (after implementation)

Checks run on 2026-10-06 (no test code exists for a sync; the checks are the factory's gates and the project suite):

- AC1: `factory sync .` printed `done: 5 created, 14 updated`, exit 0, no conflict line; `factory sync --check .` printed
  `in sync with the factory source`, exit 0.
- AC2 (deliberate break): appended one line to `.claude/skills/factory-spec/SKILL.md`; `factory sync --check .` printed
  `STALE .claude/skills/factory-spec/SKILL.md (locally modified; ...)` and exited 1. Restored the exact bytes; `--check` exited 0
  again and `git status` showed the file unmodified. This shows the check fails when a managed file is changed by hand.
- AC3: `python .factory/verify.py` printed `verify: OK` (exit 0) after the 17 status changes.
- AC4: `git diff .github/workflows/ci.yml` shows only the `uses:` lines (checkout v7 x3, setup-uv v10.2.0, setup-node v7,
  paths-filter v4); all comment blocks and `--deselect` lines are untouched.
- AC6: `grep` over `docs/work/*/item.yaml` lists every former in-review item as `merged` with a quoted `pr`; each PR state was
  `MERGED` per `gh pr view`. ADE-30 (`spec-approved`) untouched.
- AC7: `uv run python -m pytest src/tests -q -m "not integration"`: `2 failed, 1984 passed, 1 skipped, 19 deselected`; the two
  failures are `test_compact_run_not_in_executor_returns_false` (ADE-24) and `test_seeded_definitions_exist` (ADE-23).
- Also `factory doctor .`: 0 failures, 0 warnings (see notes.md).
- AC5: PR #22 check `sonarcloud` (job of workflow `sonar`) passed in 8 s; log shows the notice "The SONAR_TOKEN secret is not
  available to this run ... Nothing was scanned."; steps setup-python, setup-uv, install, tests and scan all `skipped`.
- AC8: PR #22 checks green: verify, backend (2m34s, with setup-uv v10.2.0 and checkout v7), frontend (setup-node v7), docker-build
  (paths-filter v4), sonarcloud, CodeQL and the three Analyze jobs. The only annotation is GitHub's notice about `ubuntu-latest`
  moving to Ubuntu 26 on 2026-10-19; no Node 20 deprecation warning remains.
