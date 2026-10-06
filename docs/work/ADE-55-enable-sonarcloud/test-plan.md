# ADE-55 — Test plan: Enable SonarCloud

Status: draft · Risk: low · Jira: ADE-55

Test framework and conventions found: this is a configuration change with no new code, so the checks are the workflow
file itself (parsed with PyYAML), a local simulation of the guard script, the real CI run on the pull request
(`gh pr checks --watch`) and the public SonarCloud API after the merge. The project's own suite is unchanged:
`uv run python -m pytest src/tests -q -m "not integration"` (2 known failures locally, deselected in CI).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `grep -c REPLACE_ME sonar-project.properties` and `grep -E "^sonar\.(organization\|projectKey)=" sonar-project.properties` | count 0; organisation non-empty, key `vishal7pandey_adep` | n/a: two single-line values | the sonar guard on the PR must not print the REPLACE_ME skip notice | verified |
| AC2 | integration | PyYAML load of `.github/workflows/sonar.yml`, then compare the pytest command with `ci.yml` | test step contains `-m "not integration"`, all 9 `--deselect` lines of `ci.yml`, `--cov-report=xml:coverage.xml`; `sonar.python.version=3.11` | `--cov-fail-under=80` is kept as in CI | deliberately break the test step (bad `--deselect` path or a `false` command): the `sonarcloud` PR check turns red; restored: green | verified |
| AC3 | integration | PR check `sonarcloud` (log) plus local run of the guard script with `SONAR_TOKEN=""` | on the PR: guard `enabled=true`, test and scan steps `success`, job green | n/a: the only configured state | empty secret: notice printed, `enabled=false`, exit 0 (simulated); with a `REPLACE_ME` line the guard also skips | verified |
| AC4 | integration | python urllib against `https://sonarcloud.io/api/components/search_projects`, `qualitygates/project_status`, `issues/search` (no token) | 1 project, key `vishal7pandey_adep`, gate status and issue total printed | n/a: counts only | n/a: an empty result means the first analysis did not create the project, which fails the AC | planned |
| AC5 | manual | read the scan log and the project status after the merge | no "Automatic Analysis is enabled" error in the log | n/a | if the message appears, record it and tell the owner (UI-only switch) | planned |

## Regression risk

Only the `sonar` workflow changes. The `backend`, `frontend`, `docker-build`, `factory-verify` and CodeQL checks on the PR
are the regression tests; `ci.yml` is not touched. The shared pytest command must keep its 80% coverage gate passing.

## Untestable AC

None. AC5 is a manual observation because the Automatic Analysis switch is only visible in the SonarCloud UI and indirectly
through the scan log.

## Manual checks

AC5: after the merge scan, read the `sonarcloud` job log for the Automatic Analysis conflict message; none expected. Record
the answer on ADE-55.

## Audit (after implementation)

Checks run on 2026-10-06 (no test code exists for a configuration change; the checks are the workflow file, a guard simulation,
the real CI runs on PR #23 and the public SonarCloud API):

- AC1: `sonar-project.properties` has no `REPLACE_ME`; `sonar.organization=vishal7pandey`, `sonar.projectKey=vishal7pandey_adep`.
  The scan log prints `Organization key: vishal7pandey` and `Project key: vishal7pandey_adep`.
- AC2: PyYAML parsed `.github/workflows/sonar.yml`; a script comparing it with `ci.yml` printed `deselect equal: True 9` (same nine
  lines), marker filter, `--cov-report=xml:coverage.xml` and `--cov-fail-under=80` present. Job log: `Python 3.11.17`,
  `1978 passed, 28 deselected`, total coverage 90.46%. `sonar.python.version=3.11`.
- AC2 deliberate break: changed `--cov-fail-under=80` to `100` in the sonar test step and pushed. The `sonarcloud` check failed
  (`FAIL Required test coverage of 100% not reached. Total coverage: 90.46%`, scan step skipped) while `backend` stayed green
  (it runs `ci.yml`, which was not touched). Reverted in the next commit; `sonarcloud` green again (see AC3).
- AC3 guard simulation: the guard script extracted from the workflow and run with `SONAR_TOKEN=""`: printed the notice
  "The SONAR_TOKEN secret is not available ... Nothing was scanned.", wrote `enabled=false`, exit 0. With a token set:
  `enabled=true`. With `sonar.organization=REPLACE_ME` and a token: REPLACE_ME notice, `enabled=false`, exit 0.
- AC3 on the PR: first run of `sonarcloud` (3m38s) had every step `success` (guard enabled, Set up Python, Install dependencies,
  Tests with coverage, SonarCloud scan); log: `Detected project binding: NONEXISTENT`, `Pull request 23 for merge into master`,
  `Parsing report '/home/runner/work/adep/adep/coverage.xml'`, `ANALYSIS SUCCESSFUL`, `EXECUTION SUCCESS`.
- AC4, AC5: can only be checked after the merge scan on master; the results are recorded on ADE-55 (Jira comment) and the rows stay planned here.
