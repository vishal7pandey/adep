# ADE-63 — Test plan: Apply the dependency loop: dependabot config, triage, failing runs

Status: plan-approved · Risk: low · Jira: ADE-63

Test framework and conventions found: this item changes no application code. Evidence is command output: `factory sync --check`, `factory verify`, `factory status`, the YAML parse of `dependabot.yml`, `gh` reads and the Jira tickets. Application test suites are not touched and are not rerun (CI runs them on the PR).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | manual | `factory sync --check` and `factory status` run in the worktree | exit 0 after sync; the dependency summary prints with real counts and is pasted into `notes.md` and Jira | `unknown` parts are reported as such | `sync` ran without `--force`; no conflict | pass |
| AC2 | manual | parse `.github/dependabot.yml` with PyYAML and list `(ecosystem, directory, interval, groups)` | `uv /`, `npm /frontend`, `github-actions /`, weekly, `minor-and-patch` | n/a: fixed set | no `pip` or other ecosystem; no `ignore` or `allow` | pass |
| AC3 | manual | `gh pr list --author app/dependabot --state open`; repeat after the config merge; per PR `gh pr view`, `gh pr diff`, `gh pr checks --required` | each merged PR has the four conditions written in `notes.md`/Jira | a PR with one failed condition is not merged | pre-merge snapshot had no open Dependabot PRs; no merge performed | pass (pre-merge; recheck after merge) |
| AC4 | manual | `gh run view <id> --log-failed` for both ecosystems; local reproduction in scratch copies | cause stated with log lines and the reproduction | uv and pnpm causes are different and both recorded | project causes filed; no workaround or alert dismissal | pass |

## Regression risk

`sync` rewrites managed files (AGENTS block, policies, skills): a locally modified managed file would conflict and stop the step. `verify` must stay OK. The merged `dependabot.yml` starts new Dependabot PRs; they never merge without the policy conditions.

## Untestable AC

None.

## Manual checks

All four rows are manual by nature (a configuration and operations item): the steps are the Test column; expected observations are in Happy.

## Audit (after implementation)

Manual evidence (2026-10-06): `factory sync --check` reported "in sync with the factory source";
`factory verify` reported `verify: OK`. `factory status` reported 29 open Dependabot alerts (9 high,
14 medium, 6 low), 40 code-scanning alerts (35 high, 5 medium), 0 secret-scanning alerts, 0 open
Dependabot PRs, and 27 failed Dependabot update runs in the last 7 days. PyYAML parsed the config
as exactly `uv /`, `npm /frontend`, and `github-actions /`, each weekly with a `minor-and-patch`
group and no `ignore`/`allow` keys. At triage, `gh pr list --author app/dependabot --state open`
returned no PRs, so no PR was merged. Run-log diagnosis and scratch reproductions are recorded in
`notes.md`; the resulting tickets are ADE-64 and ADE-65.
