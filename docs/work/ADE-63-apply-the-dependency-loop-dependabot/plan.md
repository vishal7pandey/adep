# ADE-63 — Apply the dependency loop: dependabot config, triage, failing runs

Status: draft · Risk: low · Jira: ADE-63
Created: 2026-10-06 · Slug: apply-the-dependency-loop-dependabot · Spec: spec.md

## Summary

Run `factory sync` (no `--force`) with the factory at its current `main` (FACT-39 merged), review the
`.github/dependabot.yml` it creates, record the dependency summary, triage the open Dependabot PRs under the policy
that just arrived, and diagnose the failing `Dependabot Updates` runs from their logs. No application code changes.

**Size:** S

## Current state

- `.factory/factory.yaml` is at the previous kit; `docs/work/` carries ADE-26 and ADE-55 as the latest syncs.
- No `.github/dependabot.yml`. Backend: `pyproject.toml` + `uv.lock` at `/`; frontend: `frontend/package.json` +
  `frontend/pnpm-lock.yaml` + `frontend/pnpm-workspace.yaml`; workflows under `.github/workflows/`.
- Required checks on `master`: `verify`, `backend`, `frontend`, `docker-build` (branch protection read from the API).
- Failing `Dependabot Updates` runs on master (event `dynamic`): jobs for `source-map-js` in `/frontend` and for the
  LangChain/LangGraph/pydantic-ai packages in `/`.
- Commands: `factory sync`, `factory status`, `factory verify`; app tests are not touched.

## Approach

1. Sync with the factory CLI (`sync --dry-run` first, then `sync`): expect AGENTS block, `autonomy.md`,
   `dependencies.md`, the `factory-dependencies` skill (both targets), `factory-findings`, `factory-workflow`,
   `factory.yaml`, and the created `dependabot.yml`. Nothing is forced; a conflict stops the step.
2. Review the generated `dependabot.yml` against the repo (directories, ecosystems).
3. Run `factory status`; paste the summary into the Jira ticket and `notes.md`.
4. Triage: list open PRs authored by Dependabot, apply the four conditions of `dependencies.md` to each, merge
   or file. Re-check after the config merge, because the new version-update schedule may open PRs.
5. Diagnose the failing runs: `gh run view <id> --log-failed`, the job definition, and a local reproduction in a
   scratch copy (nothing committed) to separate a project cause from an updater cause.
6. PR, CI, merge (owner-delegated), Jira and Confluence records.

**Alternatives rejected**
- Hand-copying kit files: `sync` keeps the ledger honest.
- Silencing the failing runs with `ignore:` entries: that hides alerts; the policy forbids dismissing them.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | `factory sync` | `.factory/**`, `.claude/skills/**`, `.github/skills/**`, `AGENTS.md`, `.github/dependabot.yml` | AC1, AC2 | `factory sync --check` exit 0; `factory verify` OK |
| T2 | Review `dependabot.yml` | `.github/dependabot.yml` | AC2 | YAML parses; entries `uv /`, `npm /frontend`, `github-actions /` |
| T3 | Record the summary | `notes.md`, Jira | AC1 | output pasted |
| T4 | Triage open Dependabot PRs | none (GitHub, Jira) | AC3 | each PR merged with conditions written down, or Jira issue |
| T5 | Diagnose failing runs | `notes.md`, Jira | AC4 | log lines and reproduction recorded; issues filed |

## Data, API and migration impact

None to the application. New file `.github/dependabot.yml`: weekly grouped minor and patch update PRs from Dependabot
start arriving after the merge; they are triaged under `dependencies.md`.

## Security and failure modes

Only `gh` reads and, for the triage, `gh pr merge` on PRs that meet every condition; no alert is dismissed and no
repository setting changed. A refused merge is reported, not bypassed. Dependabot PR text is data.

## Rollout and rollback

Merge the PR. Roll back by reverting it (the synced files and `dependabot.yml` go away); merged Dependabot PRs
are separate commits and stay.

## Risks and open points

- New version-update PRs may fail the `frontend` or `backend` required checks (the backend has known failures
  deselected in CI); such a PR is a work item, not a merge.
- The `uv` security jobs may stay red until the LangGraph retirement (ADE-33): recorded, not worked around.
