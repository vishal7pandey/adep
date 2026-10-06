# ADE-55 — Enable SonarCloud

Status: draft · Risk: low · Jira: ADE-55
Created: 2026-10-06 · Slug: enable-sonarcloud · Spec: spec.md

## Summary

Make the `sonar` workflow's test step a copy of the `backend` job's pytest command (plus the XML coverage report), install
Python 3.11 the way `ci.yml` does, align `sonar.python.version`, and keep the guard untouched. The properties file already
has the real organisation key. The PR run then performs the first real scan.

**Size:** S (under an hour of work; the rest is waiting for CI)

## Current state

- `sonar-project.properties`: `sonar.organization` now real (uncommitted edit made before the item started),
  `sonar.projectKey=vishal7pandey_adep`, `sonar.python.version=3.12`,
  `sonar.python.coverage.reportPaths=coverage.xml`, exclusions include `coverage.xml`.
- `.github/workflows/sonar.yml`: guard step, then `setup-python` 3.12, `setup-uv`, `uv sync --all-extras --all-groups`,
  `uv run --with pytest-cov python -m pytest -q --cov --cov-report=xml:coverage.xml`, then the scan action.
- `.github/workflows/ci.yml` `backend`: `setup-uv`, `uv python install 3.11`, `uv sync --all-extras`, then
  `uv run pytest src/tests/ -v --tb=short --cov=src --cov-report=term-missing --cov-fail-under=80` plus nine `--deselect`.
- `pyproject.toml`: `pytest-cov` is in the `dev` extra, so `--all-extras` provides it; `testpaths = ["src/tests"]`.
- Local commands: `uv run python -m pytest src/tests -q -m "not integration"` (2 known failures locally, deselected in CI).

## Approach

Edit only `sonar.yml` and `sonar-project.properties`. Replace the `setup-python` step with `uv python install 3.11`
(identical to `ci.yml`), use `uv sync --all-extras`, and replace the test command with the CI one plus
`-m "not integration"` and `--cov-report=xml:coverage.xml`. The smallest change that makes the Sonar job a faithful
twin of CI; copying the lines avoids inventing a different notion of "the tests".

**Alternatives rejected**
- Keep the template command and only add deselects: still 3.12 and a different dependency set than CI.
- Share one script or reusable workflow for both jobs: touches `ci.yml` (needs owner approval, larger change).
- Turn on `sonar.qualitygate.wait=true`: a first analysis with unknown issues would make the job red; later decision.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Confirm the properties file: real organisation, key `vishal7pandey_adep`, `sonar.python.version=3.11` | `sonar-project.properties` | AC1, AC2 | `grep -n "REPLACE_ME" sonar-project.properties` finds nothing; `git diff` shows the two lines |
| T2 | Mirror the CI install and test step in the sonar job | `.github/workflows/sonar.yml` | AC2 | YAML parses (`yaml.safe_load`); diff of the command against `ci.yml` shows only the added `-m` and `--cov-report=xml` |
| T3 | Simulate the guard with an empty secret | none | AC3 | run the guard script with `SONAR_TOKEN=""`: notice, `enabled=false`, exit 0 |
| T4 | Break the test step on purpose, push, see CI and sonar red, restore | `.github/workflows/sonar.yml` (temporary) | AC2, AC3 | PR check `sonarcloud` red with the broken command, green after the restore commit |
| T5 | PR, watch checks, merge on green | none | AC3 | `gh pr checks --watch`: `sonarcloud` ran the scan and passed |
| T6 | Read the project, gate and issues anonymously from the public API after the merge scan | none | AC4, AC5 | `search_projects` count 1; `project_status`; `issues/search` total; record on ADE-55 |

## Data, API and migration impact

None for the application. Config only: the `sonar` workflow and the SonarCloud properties. First analysis creates the
project `vishal7pandey_adep` in the owner's SonarCloud organisation (visible publicly if the project is public).

## Security and failure modes

The token stays in the `SONAR_TOKEN` secret and reaches only the guard and the scan steps as `env`; nothing is echoed. The
`pull_request` trigger keeps `contents: read` and the fork guard. Failure modes, all shown in the `sonarcloud` job log and
none blocking other checks: wrong organisation or key, project must be imported first, Automatic Analysis enabled
("You are running CI analysis while Automatic Analysis is enabled"), coverage-gate failure in the shared command.

## Rollout and rollback

Merge to `master`; the push scan runs once and creates the project. Rollback: revert the commit (the guard then still
works; the already created SonarCloud project can stay or be deleted in the SonarCloud UI by the owner).

## Risks and open points

- Coverage paths: `--cov=src` produces `coverage.xml` with paths relative to `src`; if Sonar shows 0% coverage the
  report mapping needs `[tool.coverage.xml] relative_files` or `sonar.sources` tuning (signal: coverage 0.0% on a first scan).
- First scan on 70 MB of `sample-data/` may be slow; signal: job time. Exclude it only if needed.
