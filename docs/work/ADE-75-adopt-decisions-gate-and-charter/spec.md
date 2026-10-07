# ADE-75 — Adopt decisions gate and charter

Status: draft · Risk: low · Jira: ADE-75
Created: 2026-10-07 · Slug: adopt-decisions-gate-and-charter

## Problem

The factory kit in this repo predates two factory features: the owner-decisions gate (FACT-46: decision records in
`docs/decisions/`, answered only by the owner with `factory decide`) and the project charter (FACT-47:
`docs/PROJECT.md`, a written definition of done and a stop rule). Today the owner's open questions live in Jira
comments and chat, and nothing says when ade is finished, so scope grows by default. One concrete open question is
waiting: what to do with CodeQL alert 52 (ADE-74), the one-time bootstrap admin key banner.

## Users and context

The repo owner, who answers decisions and approves the charter, and the agents that work in this repo, who must propose
and never accept. Grounded in: `factory sync --dry-run .` (2 created, 15 updated), the factory's
`docs/decisions/TEMPLATE.md`, `D-001`, `D-002`, `docs/PROJECT.md` and `kit/charter/PROJECT.md`, `src/api/auth.py`
(`bootstrap_admin_key`), the open Jira tickets of project ADE, the open code scanning and Dependabot alerts
(read with `gh api`), and `src/eval/pid_compare.py` (the P&ID comparison tool, baseline 0.46 +- 0.11 on 2026-10-05).

## Goals and non-goals

**Goals**
- Bring the kit to the current factory version with `factory sync .` (no `--force`): decision template, charter
  template, updated skills, policies and `verify.py`.
- Record the ADE-74 / alert 52 question as a decision record in status `proposed`, with three options and a recommendation.
- Propose the ade charter: `docs/PROJECT.md` (mode `active`, 3 to 7 done criteria with one offline-checkable reference
  each, non-goals, parked list, maintenance-mode section) and a `charter` decision record in status `proposed`.
- Create the Jira tickets the charter refers to that do not exist yet, and label the parked tickets `parked`.

**Non-goals**
- No agent accepts or rejects anything: `factory decide` is never run and no record's `status`, `decision`, `by` or
  `at` is written by hand. Accepting is the owner's act.
- No change to application code, tests or dependencies, and no change to `src/api/auth.py`: the alert 52 decision is
  the owner's; the code stays as it is.
- No dismissal in CodeQL and no closing or moving of the parked tickets.
- No new evaluation run: the C1 summary file is created only when real numbers from an existing run are available (see
  Assumptions).

## Requirements

- R1. The sync must update or create exactly the files the dry run lists, never overwrite a locally modified managed
  file (no `--force`), and leave `sync --check` clean.
- R2. `.factory/verify.py` must pass on the branch, including the validation of the new records and the charter.
- R3. A decision record for alert 52 must exist in `docs/decisions/` with status `proposed`, at least two options with
  exactly one recommended, the alert URL, and `jira: ADE-74`.
- R4. `docs/PROJECT.md` must be a valid charter (`validate_charter`) naming the charter decision record, and the
  `charter` record must carry `subject: docs/PROJECT.md` and status `proposed`.
- R5. `factory status` and `factory doctor` must show both records as waiting for the owner and the charter as proposed
  but not approved.
- R6. Every Jira key in the charter must exist; parked tickets carry the label `parked` and a comment explaining why.
- R7. The project's tests must be unchanged: exactly 2 known failures (ADE-23, ADE-24) in the non-integration run.

## Acceptance criteria

- AC1. `factory sync .` (no `--force`) reports 2 created and 15 updated with no conflict; `factory sync --check .` exits 0
  afterwards; with one managed file edited by hand `--check` exits non-zero and exits 0 again once restored. (R1)
- AC2. `python .factory/verify.py` exits 0 on the branch, and it exits non-zero when a decision record is hand-edited to
  `status: accepted` without a `decision` (the deliberate break). (R2)
- AC3. `docs/decisions/D-001-*.md` has `type: dismissal` or `design` as the validator accepts, `status: proposed`,
  `jira: ADE-74`, three options of which exactly one is `recommended: true`, and `decision`, `by`, `at` null. (R3)
- AC4. `docs/PROJECT.md` has `mode: active`, `decision: D-002`, 3 to 7 `done` entries each with exactly one `check`, and
  `docs/decisions/D-002-*.md` has `type: charter`, `subject: docs/PROJECT.md`, `status: proposed`. (R4)
- AC5. `factory status` lists D-001 and D-002 as waiting for the owner; `factory doctor .` warns `no approved charter`
  and reports no failure; `factory inbox` lists both. (R5)
- AC6. The tickets named by the charter exist (checked by reading each key); the four parked tickets (ADE-16, ADE-17,
  ADE-20, ADE-21) carry the label `parked` and a comment; none is closed or transitioned. (R6)
- AC7. `uv run python -m pytest src/tests -q -m "not integration"` shows exactly 2 failures,
  `test_compact_run_not_in_executor_returns_false` and `test_seeded_definitions_exist`, and no others;
  `ruff format --check` passes on the touched Python files (none are expected). (R7)
- AC8. The pull request's required checks (`verify`, `backend`, `frontend`, `docker-build`, `sonarcloud`, `CodeQL`) are
  green before merge. (R1, R2)

## Edge cases and failure modes

- `factory decide` is refused for an unfilled record or a changed subject; the records are written in full, with no
  `REPLACE_ME`, so the owner can answer them directly.
- A `metric` reference needs a file that holds real numbers. The file `docs/eval/pid-latest.json` is committed only with
  values copied from the 2026-10-05 baseline run (0.46 mean count recall, 0.11 spread); the criterion stays not met
  until a new run meets the bar.
- The `jira:` reference is `unknown` offline by default; criteria that use it show `unknown`, not met, until the lookup
  is injected. This is the factory's documented behaviour.

## Non-functional requirements

- Security (`.factory/policies/security.md`): no secret, `.env` content or key value appears in any file or comment; the
  alert 52 record names the code location, never a key.
- Autonomy (`.factory/policies/autonomy.md`): decisions and charters are never accepted by an agent.

## Assumptions

- The recommended option for alert 52 is to dismiss as `won't fix` (a documented one-time console banner for a local
  single-operator tool). The owner can choose option 2 or 3 instead; that would open a bug for the code change.
- 0.8 mean count recall is the agent's proposed bar for the new engine on the three DEXPI reference drawings. It is the
  owner's number to change; the C1 ticket says so.
- C6 is an umbrella ticket for open high findings; it is closed by the owner only when the scanners show none.
- ADE-33 (delete the old engine) needs the owner's fresh go-ahead before any work starts; the charter does not give it.

## Risks and dependencies

Low risk: documentation, kit files and Jira labels only, easily reverted. The factory's charter reading of `jira`
references depends on a lookup that is not wired by default (criteria show `unknown`); noted in Edge cases.

## Open questions

None open: the owner's answers (record D-001 and the charter record D-002) are the deliverable.
