# ADE-63 — Apply the dependency loop: dependabot config, triage, failing runs

Status: draft · Risk: low · Jira: ADE-63
Created: 2026-10-06 · Slug: apply-the-dependency-loop-dependabot

## Problem

The factory now ships a dependency loop (factory ticket FACT-39: policy `dependencies.md`, skill
`factory-dependencies`, a `dependabot.yml` template, a dependency summary in `factory status`). ade has none of it:
no `.github/dependabot.yml` (no schedule, no grouping, no version updates), no rule for when an agent may merge a
Dependabot PR, and nothing that shows open alerts, open Dependabot PRs and failed `Dependabot Updates` runs.
Those runs are failing on master today (a `source-map-js` security job in `/frontend`, and `uv` jobs in `/`), and
nobody has diagnosed why.

## Users and context

The owner and the coding agent working in this repo (backend `uv` at `/`, frontend `pnpm` in `/frontend`, GitHub
Actions). Grounded in `.factory/policies/dependencies.md` (after sync), `docs/ARCHITECTURE.md` of the factory
(Treaty 3.10), the failing runs' logs (`gh run view <id> --log-failed`) and `frontend/package.json`,
`frontend/pnpm-lock.yaml`, `frontend/pnpm-workspace.yaml`.

## Goals and non-goals

**Goals**
- The new policy, skill and AGENTS block reach this repo through `factory sync` (no `--force`).
- `.github/dependabot.yml` for the ecosystems ade uses.
- The dependency summary printed and recorded; every open Dependabot PR merged under the policy or filed.
- The cause of the failing Dependabot Updates runs found and recorded; fixed if it is a configuration problem.

**Non-goals**
- Other findings: no alert is filed, fixed or dismissed here (ADE-56..62 and the alert backlog are separate).
- SonarCloud setup; ADE application code; CI changes.

## Requirements

- R1. `factory sync` lays in the policy, skills and AGENTS block, leaving locally modified managed files alone.
- R2. `.github/dependabot.yml` has entries for `uv` at `/`, `npm` at `/frontend` (pnpm lockfile) and
  `github-actions` at `/`, weekly, grouped minor and patch.
- R3. The output of `factory status` (dependency summary) is recorded on ADE-63 and in `notes.md`.
- R4. Each open Dependabot PR is triaged against the four conditions of the policy: merged when all hold, else a
  Jira issue states the failed condition and the PR stays open.
- R5. The failing `Dependabot Updates` runs are diagnosed from their logs; the cause is recorded, and a
  configuration cause is fixed in `dependabot.yml` or the repo, otherwise an issue is filed.

## Acceptance criteria

- AC1. (R1, R3) After sync, `factory sync --check` is clean and `factory status` prints the dependency summary;
  its output is on the Jira ticket and in `notes.md`.
- AC2. (R2) `.github/dependabot.yml` parses and lists exactly `uv /`, `npm /frontend`, `github-actions /`, each
  weekly with a `minor-and-patch` group.
- AC3. (R4) Every Dependabot PR open at triage time is either merged (all four conditions checked and written down)
  or has a Jira issue naming the failed condition; none is merged that fails a condition.
- AC4. (R5) The cause of the failing runs is stated with evidence (log lines), with a fix merged or an issue filed.
