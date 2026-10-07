# ADE-75 — Test plan: Adopt decisions gate and charter

Status: draft · Risk: low · Jira: ADE-75

Test framework and conventions found: no application code changes, so no new unit tests. The tests are the factory's
own gates plus the project's existing suite: `factory sync --check`, `.factory/verify.py` (validates decision records
and the charter), `factory status`, `factory doctor`, `factory inbox`, CI on the pull request, and
`uv run python -m pytest src/tests -q -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `factory sync .` then `factory sync --check .` | sync: 2 created, 15 updated, check exit 0 | n/a: a second `--check` run is unchanged | edit `.claude/skills/factory-spec/SKILL.md` by hand: `--check` reports it and exits non-zero; restored: exit 0 | verified |
| AC2 | integration | `python .factory/verify.py` | exit 0 with the two records and the charter | n/a: the validator's rules are the factory's | a record hand-edited to `status: accepted` with null `decision`: verify prints an error and exits non-zero (deliberate break, then reverted) | verified |
| AC3 | integration | `python .factory/verify.py` plus a read of `docs/decisions/D-001-*.md` | type, status `proposed`, `jira: ADE-74`, 3 options, 1 recommended | the dismissal-only fields (`alert`, `reason: won't fix`) present if the type is `dismissal` | n/a: covered by AC2's negative | verified |
| AC4 | integration | `python .factory/verify.py`; `factory status` | charter valid: 3 to 7 criteria, one check each; charter record has `subject` | exactly 7 criteria is the upper bound; none exceeds it | n/a: a bad criterion would make verify fail (AC2 shows the failure mode) | verified |
| AC5 | integration | `factory status`, `factory doctor .`, `factory inbox` | both records listed as waiting; doctor WARN `no approved charter`, 0 failures | n/a | n/a: nothing is accepted, so there is no state to be wrongly shown | verified |
| AC6 | manual | read each Jira key and label back | all referenced keys exist; four labelled `parked` | n/a | none closed or transitioned (status unchanged) | verified |
| AC7 | integration | `uv run python -m pytest src/tests -q -m "not integration"`; `ruff format --check` | only the known failures: the two (ADE-23, ADE-24), plus in a checkout without `.env` the seven no-credentials e2e tests CI deselects | n/a: no code changed | a failure outside CI's deselect list would be a regression | verified |
| AC8 | integration | `gh pr checks --watch` | verify, backend, frontend, docker-build, sonarcloud, CodeQL green | n/a | a red check blocks the merge | verified |

## Regression risk

The only behaviour that can change is the factory's own tooling and CI (`verify.py` is new, the factory-verify workflow
runs it). The application and its tests do not change; the baseline of 2 known failures must hold.

## Untestable AC

None.

## Manual checks

AC6: for each of the new tickets and ADE-14, 16, 17, 18, 20, 21, 32, 33, 42, 65, 74 read the issue in Jira; confirm the
four parked tickets show the label `parked` and their status is unchanged.

## Audit (after implementation)

Checks run on 2026-10-07 (no test code exists for this change; the checks are the factory's gates and the project suite):

- AC1: `factory sync --dry-run .` listed 2 created, 15 updated; `factory sync .` (no `--force`) printed `done: 2 created, 15 updated`,
  exit 0, no conflict; `factory sync --check .` printed `in sync with the factory source`, exit 0. Deliberate break: appended a line to
  `.claude/skills/factory-spec/SKILL.md`; `--check` printed `STALE .claude/skills/factory-spec/SKILL.md (locally modified; ...)` and exited 1;
  restored the exact bytes; `--check` exited 0 and `git status` showed the file unmodified.
- AC2 (deliberate break): set `status: accepted` by hand in `D-001`; `python .factory/verify.py` printed three `FAIL D-001: status is
  accepted but 'by' / 'at' / 'decision' ...` lines and exited 1; reverted to `proposed`; `verify: OK`, exit 0. No `factory decide` was run.
- AC3/AC4: `verify: OK` with D-001 (`dismissal`, `alert`, `reason: won't fix`, 3 options, one recommended, `jira: ADE-74`) and D-002
  (`charter`, `subject: docs/PROJECT.md`). `charter.validate_charter` on the draft returned no problem; six criteria evaluated as C1 `not met`
  (0.46 below 0.8) and C2 to C6 `unknown` without a Jira lookup (`not met` with a stub that answers `To Do`).
- AC5: `factory status` printed `waiting for the owner (2 decisions)` D-001 and D-002 and `charter: no approved charter - decision D-002 is
  waiting for the owner`; `factory doctor .` printed `WARN decision D-001`, `WARN decision D-002`, `WARN charter`, `0 failure(s)`. (`factory
  inbox` reads the factory registry, which points at the main checkout, so it does not list a worktree; `status` and `doctor` do.)
- AC6: ADE-76 (C1), ADE-77 (js-yaml high alert 8), ADE-78 (C6 umbrella) created; ADE-16, 17, 20, 21 labelled `parked` with a comment, status
  unchanged (To Do); ADE-33 commented (needs the owner's go-ahead).
- AC7: `uv run --frozen --all-extras python -m pytest src/tests -q -m "not integration"` in this clean worktree (no `.env`):
  `9 failed, 2230 passed, 6 skipped, 19 deselected`. The nine are exactly CI's `--deselect` list: the two known ones
  (`test_compact_run_not_in_executor_returns_false` ADE-24, `test_seeded_definitions_exist` ADE-23) plus seven e2e tests that fail
  only because no LLM provider is configured (`RuntimeError: No LLM provider configured`), which also shows in a checkout without `.env`.
  No test touches code changed here (none changed); no Python file was edited, so `ruff format` has nothing to check.
- AC8: filled in with the PR checks below.
