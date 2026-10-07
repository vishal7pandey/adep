# ADE-75 — Adopt decisions gate and charter

Status: draft · Risk: low · Jira: ADE-75
Created: 2026-10-07 · Slug: adopt-decisions-gate-and-charter · Spec: spec.md

## Summary

Sync the factory kit (decision template, charter template, updated skills, policies, `verify.py`), then write three
proposals as files: a decision record for the ADE-74 alert 52 question, the ade charter `docs/PROJECT.md`, and the
charter decision record. Create the Jira tickets the charter needs and label the parked ones. Everything stays
`proposed`: the owner answers with `factory decide`.

**Size:** S (under half a day)

## Current state

- Kit last synced in ADE-26 (factory 0.1.0 files, no `docs/decisions/`, no `docs/PROJECT.md`). `factory sync --dry-run .`
  lists 2 created (`docs/decisions/TEMPLATE.md`, `docs/PROJECT.md`) and 15 updated (AGENTS.md block, `verify.py`, two
  policies, ten skill files, `factory.yaml`).
- `docs/work/` holds 31 work items, all merged except this one. ADE-74 is `merged` (PR 40) but its alert 52 successor is open.
- Open Jira tickets read on 2026-10-07: ADE-14, 16, 17, 18, 20, 21, 32, 33, 42, 65, 74 (and others not used here).
- Open scanner alerts read with `gh api`: code scanning 52 (high), Dependabot highs on the LangChain/LangGraph/
  pydantic-ai stack (blocked until ADE-33, ticket ADE-65) and `js-yaml` (alert 8, frontend lockfile, no ticket yet).
- Tests: `uv run python -m pytest src/tests -q -m "not integration"` (2 known failures: ADE-23, ADE-24).

## Approach

Use the factory's own commands for everything it can do (`sync`, `decision new`, `status`, `doctor`, `verify`), and
write the prose of each record by hand. No application code changes. The charter's `done` references use the four
kinds the validator accepts, preferring `work`, `file` and `metric` (checked offline) and using `jira` where only a
ticket can say it (C2 to C5, C6), so the owner sees the criterion as `unknown` until a lookup is wired rather than as
a false `met`.

**Alternatives rejected**
- `factory sync --force`: would overwrite local edits; not needed, the dry run shows no conflict.
- Creating a `fix` ticket for option 2 or 3 of the alert 52 record now: the owner has not chosen; the option text says
  a bug would be opened after the choice.
- One criterion per finding ticket for security: more than 7 criteria; a single umbrella ticket carries C6.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Sync the kit, no `--force`; check it is in sync | factory-managed files, `docs/PROJECT.md`, `docs/decisions/TEMPLATE.md` | AC1, AC2 | `factory sync --dry-run .`, `factory sync .`, `factory sync --check .`, `python .factory/verify.py` |
| T2 | Create the missing Jira tickets (C1, C6 umbrella, js-yaml finding) and the `docs/eval/pid-latest.json` summary | Jira, `docs/eval/pid-latest.json` | AC4, AC6 | read each key back; `jq` over the file |
| T3 | Write decision record D-001 (alert 52) | `docs/decisions/D-001-*.md` | AC3 | `verify.py`; `factory decision` listing |
| T4 | Write `docs/PROJECT.md` and charter record D-002 | `docs/PROJECT.md`, `docs/decisions/D-002-*.md` | AC4, AC5 | `verify.py`; `factory status`; `factory doctor .`; `factory inbox` |
| T5 | Label ADE-16, 17, 20, 21 `parked` and comment | Jira | AC6 | read the labels back |
| T6 | Run the project checks, open the PR, wait for CI, merge | PR | AC7, AC8 | pytest, `ruff format --check`, `gh pr checks` |

## Data, API and migration impact

None for the application. New files: `docs/decisions/`, `docs/PROJECT.md`, `docs/eval/pid-latest.json`. The records and
the charter are plain files; a later accept stamps a hash of `docs/PROJECT.md`, after which edits need a new decision.

## Security and failure modes

No secret is read or written; `.env` is never opened. The records name `src/api/auth.py` and the alert URL only. If the
validator rejects a record or the charter, `verify` fails on the PR and the fix is to edit the proposal. An agent never
runs `factory decide`.

## Rollout and rollback

Merge to master after green CI. Roll back by reverting the merge commit; Jira labels are removed by hand. Point of no
return: none (the owner's later `decide` is the owner's own action).

## Risks and open points

- The `jira` reference lookup is not wired by default, so C2 to C6 show `unknown`; signal: `factory status` output.
- `docs/eval/pid-latest.json` must not invent numbers; signal: it contains only the 2026-10-05 baseline values.
