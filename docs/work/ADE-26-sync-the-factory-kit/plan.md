# ADE-26 — Sync the factory kit

Status: draft · Risk: low · Jira: ADE-26
Created: 2026-10-06 · Slug: sync-the-factory-kit · Spec: spec.md

## Summary

Run `factory sync .` (no `--force`) from the factory CLI to refresh the managed files and add the dormant
SonarCloud scan, hand-edit the user-owned `ci.yml` for Node 24 capable actions only, and set the status of every
merged work item to `merged`. Verify with `sync --check`, `verify.py`, `factory doctor` and the real test run.

**Size:** S

## Current state

- Factory kit adopted in PR #1; `.factory/factory.yaml` has `factory_version: 0.1.0` and a `managed:` hash map.
- `factory sync --dry-run .` plans 5 created (`.github/workflows/sonar.yml`, `sonar-project.properties`,
  `.factory/policies/findings.md`, `factory-findings` skill in `.claude/skills` and `.github/skills`) and 14 updated
  (`AGENTS.md` block, `factory-verify.yml`, `.factory/verify.py`, policies `autonomy` and `security`, skills
  `implement`, `release`, `test`, `workflow` in both skill dirs, `factory.yaml`). `ci.yml`, `CLAUDE.md`, CODEOWNERS,
  PR template, `docs/work/README.md` are user-owned and skipped.
- `ci.yml` uses `actions/checkout@v4`, `astral-sh/setup-uv@v3`, `actions/setup-node@v4`, `dorny/paths-filter@v3`.
  The factory kit templates use checkout v7, setup-node v7, setup-uv v10.2.0 (all Node 24). paths-filter v3 is
  Node 20; v4 declares `node24`.
- Commands: `uv run python -m pytest src/tests -q -m "not integration"` (2 known failures), `python .factory/verify.py`.
- 17 items are `in-review` and every PR is merged; most have `pr: null`.

## Approach

Use the tool for everything it owns (sync, advance) and hand-edit only the user-owned file. Smallest change: no
re-formatting of `ci.yml`, only the `uses:` lines. Sonar stays dormant because the template guards on the missing
org key and token; nothing is filled in.

**Alternatives rejected**
- `sync --force`: would overwrite local edits to managed files; none expected, and the rule is to stop if one exists.
- Replacing `ci.yml` with the kit template: would drop the project's disabled-step conventions and deselect list.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Review `sync --dry-run .`, run `sync .` without `--force` | managed files listed above, `.factory/factory.yaml` | AC1 | output shows 5 created, 14 updated, no conflict |
| T2 | `sync --check .`, then deliberate break: edit one managed file, `--check` must report it, restore | one skill file (temporary) | AC1, AC2 | exit codes 0, non-zero, 0 |
| T3 | Bump `uses:` versions in `ci.yml` only | `.github/workflows/ci.yml` | AC4 | `git diff` shows only `uses:` lines; comments unchanged |
| T4 | `gh pr view <n> --json state` for each in-review item, then `factory advance <ID> merged --pr <n>`; fix `pr` to a string if the CLI writes a URL | `docs/work/*/item.yaml` | AC6 | `grep` of status and pr in all items |
| T5 | `python .factory/verify.py`; `factory doctor .` | none | AC3 | exit 0; doctor lines recorded in notes |
| T6 | Run the non-integration backend tests | none | AC7 | 2 failures, the two known ones |
| T7 | Fill test-plan audit, commit with explicit paths, push, open PR, wait for CI, merge | work item docs | AC5, AC8 | `gh pr checks --watch` green, `sonar` shows the notice |

## Data, API and migration impact

None. No application code, schema, endpoint or dependency changes. `factory.yaml` hashes are rewritten by sync.

## Security and failure modes

No secret is read, set or printed; `.env` is not opened. The sonar workflow runs with the factory's read-only
permissions and skips with a notice when `SONAR_TOKEN` or the org key are missing. If an action bump breaks a job,
CI on the PR shows it; revert that bump and note it.

## Rollout and rollback

Merge the PR. Rollback is `git revert` of the merge commit (all changes are in files; sync is idempotent).
No point of no return.

## Risks and open points

- `setup-uv` jumps from v3 to v10.2.0: the CI run shows whether `uv sync --all-extras` still works.
- `factory advance` may write the PR as a URL or not at all for items already past `in-review`: then edit the
  `pr` value with the Edit tool.
