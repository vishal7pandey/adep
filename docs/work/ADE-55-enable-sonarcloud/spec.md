# ADE-55 — Enable SonarCloud

Status: draft · Risk: low · Jira: ADE-55
Created: 2026-10-06 · Slug: enable-sonarcloud

## Problem

ADE-26 synced the factory's SonarCloud scan into this repo in a dormant state: the `sonar` workflow skips every step
after its guard because the `SONAR_TOKEN` secret and the real organisation key did not exist. On 2026-10-06 the
owner supplied both (the token was validated against the SonarCloud API; the organisation exists with 0 projects) and
`SONAR_TOKEN` is now a GitHub Actions secret on this repo. Once the guard stops skipping, the template's test step
would run `pytest` on Python 3.12 with no marker filter and no deselects, which is not how this project's own CI runs
its tests (Python 3.11, nine known clean-checkout failures deselected). It would go red or report different coverage
than CI. Nothing is analysed until this is fixed.

## Users and context

The repo owner and the agents working in `C:\Dev\projects\ade`. The change lives in `sonar-project.properties` and
`.github/workflows/sonar.yml` (both create-mode files owned by this project, not managed by `factory sync`).
Grounded in: `.github/workflows/ci.yml` (job `backend`), `AGENTS.md` (commands and the CI note), `pyproject.toml`
(`[tool.pytest.ini_options]`, `pytest-cov` in the `dev` extra) and the factory's `docs/sonarcloud.md`.

## Goals and non-goals

**Goals**
- Real `sonar.organization` and `sonar.projectKey=vishal7pandey_adep` in `sonar-project.properties`.
- The `sonar` job runs the project's backend tests exactly the way `ci.yml` does, on the same Python version, and
  writes the coverage XML where `sonar-project.properties` expects it.
- On the pull request the guard no longer skips and the scan runs; the first analysis creates the project.
- After the merge the project exists in the organisation with a first analysis whose quality gate status and issue
  count are recorded on the Jira ticket.

**Non-goals**
- No change to `ci.yml`, to application code, tests or dependencies.
- No change to the guard logic: it must still skip (green) when the secret is empty, on fork pull requests and while a
  `REPLACE_ME` value remains.
- The quality gate does not fail the job (`sonar.qualitygate.wait` stays off); the first results are recorded, not enforced.
- Fixing the findings Sonar reports, and the factory template itself (FACT-40), are out of scope.
- Automatic Analysis can only be switched in the SonarCloud UI; this change only reports its state.

## Requirements

- R1. `sonar-project.properties` must hold the real organisation key and `sonar.projectKey=vishal7pandey_adep`.
- R2. The `sonar` job's test step must run the same command as the `backend` job in `ci.yml` (same marker filter,
  same `--deselect` list, same Python version, same dependency install), plus the coverage XML report at the path in
  `sonar.python.coverage.reportPaths`.
- R3. `sonar.python.version` must equal the Python version CI uses.
- R4. The guard must keep skipping with a notice and a green job when `SONAR_TOKEN` is empty.
- R5. With the token present and no placeholder left, the job must run the scan and the first analysis must create the
  project in the organisation.
- R6. The outcome of the first analysis (project count, gate status, issue count, Automatic Analysis conflict or not)
  must be recorded on ADE-55.

## Acceptance criteria

- AC1. (R1) `sonar-project.properties` has no `REPLACE_ME`, a non-empty `sonar.organization`, and
  `sonar.projectKey=vishal7pandey_adep`, the repository being `vishal7pandey/adep`.
- AC2. (R2, R3) The `sonar` job's test step uses `-m "not integration"` and all nine `--deselect` lines from `ci.yml`,
  Python 3.11 installed the same way as in `ci.yml`, `uv sync --all-extras`, and `--cov-report=xml:coverage.xml`;
  `sonar.python.version=3.11`.
- AC3. (R4, R5) On the pull request the `sonarcloud` job's guard step reports enabled, the test and scan steps run (not
  skipped) and the job is green; if SonarCloud rejects the project (wrong key, project must be imported first, Automatic
  Analysis enabled) the exact message from the job log is recorded on the ticket. Failure path: with `SONAR_TOKEN` empty,
  the guard step writes `enabled=false`, prints the notice and exits 0 (simulated locally).
- AC4. (R5, R6) After the merge, `components/search_projects?organization=<org>` returns 1 project with key
  `vishal7pandey_adep` (was 0), and its quality gate status and open issue count are recorded on the ticket.
- AC5. (R6) The ticket states whether Automatic Analysis conflicts with the CI scan; if it does, the owner is told it can
  only be switched off in the SonarCloud UI.

## Edge cases and failure modes

- A fork or Dependabot pull request has no secrets: the job's `if:` and the guard keep it green and skipped (unchanged).
- A test in the deselected list starts passing: the deselect is harmless and is removed together with the same line in
  `ci.yml` when its ticket (ADE-23, ADE-24) is done.
- The coverage gate (`--cov-fail-under=80`) is part of the shared command, so a coverage drop fails both jobs the same way.
- SonarCloud outage or a rejected key fails only the `sonarcloud` job; no other check depends on it.

## Non-functional requirements

- Security (`.factory/policies/security.md`): the token is read only from the `SONAR_TOKEN` secret, never printed or
  committed; the organisation key is not a secret. No `.env` is opened.
- Cost and time: the job now runs the whole backend suite, about the same duration as the `backend` job.

## Assumptions

- The organisation key the owner supplied is the one in `sonar-project.properties` (already edited in the working tree).
- Python 3.11 is the version to match: `ci.yml` installs 3.11 and `AGENTS.md` records that CI uses 3.11.
- `ci.yml` does not pass `-m "not integration"` today (integration tests skip without credentials on the runner); the
  sonar step adds it anyway as a safeguard so it can never call a paid API. This is the only deliberate difference.
- Repeating the `--deselect` list in two workflows is acceptable for now (simplest, no CI change); a shared script is a
  later cleanup.

## Risks and dependencies

Low: the change touches one workflow that nothing else depends on and is fully reverted by reverting the commit. It
depends on the owner's SonarCloud organisation and token being valid (validated on 2026-10-06) and on Automatic
Analysis being off for the new project.
