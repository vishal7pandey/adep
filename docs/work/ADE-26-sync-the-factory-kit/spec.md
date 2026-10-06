# ADE-26 — Sync the factory kit

Status: draft · Risk: low · Jira: ADE-26
Created: 2026-10-06 · Slug: sync-the-factory-kit

## Problem

The factory kit in this repo was adopted on 2026-10-04 and is now behind the factory. Since then the factory merged
FACT-15 (GitHub Actions bumped to Node 24 capable versions; the Node 20 runtimes are being retired by GitHub),
FACT-12 (new `verify.py` behaviour, `factory sync --check`, docs-only rule), the findings policy and skill, and an
optional SonarCloud scan. Until the repo is synced its CI runs deprecated action versions, `verify.py` lacks the new
rules, and the agents' skills and policies are out of date. Seventeen work items also still say `in-review` although
their pull requests merged long ago.

## Users and context

The repo owner and the agents that work in `C:\Dev\projects\ade`. The change lives in the factory-managed files
(`.factory/`, `.claude/skills`, `.github/skills`, the `AGENTS.md` block, `.github/workflows/factory-verify.yml`)
plus two new files for the SonarCloud scan, and in the user-owned `.github/workflows/ci.yml`. Grounded in:
`factory sync --dry-run .` (5 created, 14 updated), `AGENTS.md`, `docs/jira-workflow.md` in the factory repo,
`kit/ci/python.yml` and `kit/sonar/python.yml` in the factory repo.

## Goals and non-goals

**Goals**
- Bring every factory-managed file to the current factory version using `factory sync`, without overwriting any
  locally modified managed file.
- Move the actions in the user-owned `ci.yml` to Node 24 capable versions (FACT-15) and keep the project's own
  disabled-step conventions (ruff ADE-20, mypy ADE-21, frontend lint ADE-28, docker build ADE-27).
- Add the SonarCloud scan in its dormant state: the new `sonar` job runs, prints a notice and skips the rest until
  the owner supplies the organisation key and the `SONAR_TOKEN` secret.
- Make work-item statuses true: every `in-review` item whose pull request is merged becomes `merged`, with `pr`
  recorded as a string (FACT-20 convention).

**Non-goals**
- No SonarCloud organisation key, project key value or token is invented or set; no secret is touched.
- No other change to `ci.yml` (no new steps, no re-enabling of disabled steps, no coverage or test changes).
- No application code, test or dependency change; test results must not move.
- Items that are not `in-review` (ADE-30, `spec-approved`, docs-only PR #7) are left as they are.

## Requirements

- R1. The system (the sync) must update or create exactly the files the dry run lists, never overwrite a locally
  modified managed file (no `--force`), and leave `sync --check` clean afterwards.
- R2. `python .factory/verify.py` must pass on the branch with the new verify script.
- R3. `ci.yml` must reference Node 24 capable versions of every action it uses and must keep its disabled-step
  comments and tickets unchanged.
- R4. The new `sonar` job must be green while dormant (notice printed, scan steps skipped) and must contain no
  invented value or secret.
- R5. Every `docs/work/*/item.yaml` that is `in-review` with a merged PR must read `status: merged` and
  `pr: "<number>"` (string).
- R6. The project's test results must be unchanged: the non-integration backend run still has exactly the two
  known failures (ADE-23, ADE-24).

## Acceptance criteria

- AC1. `factory sync .` (no `--force`) reports 5 created, 14 updated and no conflict; afterwards
  `factory sync --check .` exits 0. (R1)
- AC2. Failure path: after editing one managed file locally, `factory sync --check .` reports it and exits non-zero;
  after restoring the file it exits 0 again. (R1)
- AC3. `python .factory/verify.py` exits 0. (R2, R5)
- AC4. In `.github/workflows/ci.yml`, `actions/checkout`, `actions/setup-node`, `astral-sh/setup-uv` and
  `dorny/paths-filter` use the versions the factory kit templates use or, where the kit has none (paths-filter),
  the latest major whose `action.yml` declares `node24`; the comment blocks for ADE-1/ADE-20/ADE-21/ADE-27/ADE-28
  and the `--deselect` list are byte-for-byte unchanged. (R3)
- AC5. On the pull request the `sonar` check runs and succeeds, its log shows the "skipping" notice, and
  `sonar-project.properties` / `sonar.yml` hold only the factory's placeholders. (R4)
- AC6. The seventeen `in-review` items with merged PRs (ADE-1, ADE-4, ADE-5, ADE-15, ADE-19, ADE-29, ADE-31, ADE-34
  to ADE-41, ADE-45, ADE-51 as found by listing) are `merged` with a string `pr`; each PR's state was read with
  `gh pr view` first. No item has `pr: null` while `merged`. (R5)
- AC7. `uv run python -m pytest src/tests -q -m "not integration"` shows exactly 2 failures,
  `test_compact_run_not_in_executor_returns_false` and `test_seeded_definitions_exist`, and no others. (R6)
- AC8. The pull request's required checks (`verify`, `backend`, `frontend`, `docker-build`, plus `sonar` and
  CodeQL) are green before merge. (R1, R3, R4)

## Edge cases and failure modes

- A locally modified managed file: sync reports a conflict and does not write it; the work stops and is reported
  on the ticket (AC1 would then not hold). Expected: none today.
- `ci.yml` is user-owned and skipped by sync; it is edited by hand and only for action versions.
- A newer action major changes behaviour (for example `setup-uv` v3 to v10): CI on the pull request is the proof;
  if a job breaks, revert that one bump and record why in `notes.md`.
- The sonar guard cannot be tested for the configured state here (no key, no token): out of scope, it is the
  factory's tested template.

## Non-functional requirements

- Security (`.factory/policies/security.md`): no secret read, written or printed; `.env` is never opened; workflow
  permissions come from the factory template as shipped.
- Compatibility: `.factory/factory.yaml` `managed:` hashes are rewritten by sync only.

## Assumptions

- The owner delegated spec and plan approval and the merge for this item (recorded as delegated approvals).
- The latest tags checked on 2026-10-06 are `actions/checkout` v7, `actions/setup-node` v7, `astral-sh/setup-uv`
  v10.2.0 (the same the kit uses) and `dorny/paths-filter` v4 (node24).
- Merged PR numbers come from the branch names (`gh pr list --state all`): ADE-1 #4, ADE-4 #5, ADE-5 #6, ADE-15 #15,
  ADE-19 #3, ADE-29 #18, ADE-31 #17, ADE-34 #8, ADE-35 #9, ADE-36 #10, ADE-37 #11, ADE-38 #12, ADE-39 #13,
  ADE-40 #14, ADE-41 #16, ADE-45 #20, ADE-51 #21.

## Risks and dependencies

Risk low: configuration and documentation only, reversible by reverting the commit. The one real risk is a CI job
breaking on a newer action major; the pull request run shows it before merge. Dependency: the factory repo at
`C:\Dev\ai-software-factory` (FACT-12, FACT-15, FACT-35).
