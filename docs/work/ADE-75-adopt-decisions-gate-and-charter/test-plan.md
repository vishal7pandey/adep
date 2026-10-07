# ADE-75 — Test plan: Adopt decisions gate and charter

Status: draft · Risk: low · Jira: ADE-75

Test framework and conventions found: no application code changes, so no new unit tests. The tests are the factory's
own gates plus the project's existing suite: `factory sync --check`, `.factory/verify.py` (validates decision records
and the charter), `factory status`, `factory doctor`, `factory inbox`, CI on the pull request, and
`uv run python -m pytest src/tests -q -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `factory sync .` then `factory sync --check .` | sync: 2 created, 15 updated, check exit 0 | n/a: a second `--check` run is unchanged | edit `.claude/skills/factory-spec/SKILL.md` by hand: `--check` reports it and exits non-zero; restored: exit 0 | planned |
| AC2 | integration | `python .factory/verify.py` | exit 0 with the two records and the charter | n/a: the validator's rules are the factory's | a record hand-edited to `status: accepted` with null `decision`: verify prints an error and exits non-zero (deliberate break, then reverted) | planned |
| AC3 | integration | `python .factory/verify.py` plus a read of `docs/decisions/D-001-*.md` | type, status `proposed`, `jira: ADE-74`, 3 options, 1 recommended | the dismissal-only fields (`alert`, `reason: won't fix`) present if the type is `dismissal` | n/a: covered by AC2's negative | planned |
| AC4 | integration | `python .factory/verify.py`; `factory status` | charter valid: 3 to 7 criteria, one check each; charter record has `subject` | exactly 7 criteria is the upper bound; none exceeds it | n/a: a bad criterion would make verify fail (AC2 shows the failure mode) | planned |
| AC5 | integration | `factory status`, `factory doctor .`, `factory inbox` | both records listed as waiting; doctor WARN `no approved charter`, 0 failures | n/a | n/a: nothing is accepted, so there is no state to be wrongly shown | planned |
| AC6 | manual | read each Jira key and label back | all referenced keys exist; four labelled `parked` | n/a | none closed or transitioned (status unchanged) | planned |
| AC7 | integration | `uv run python -m pytest src/tests -q -m "not integration"`; `ruff format --check` | exactly the two known failures | n/a: no code changed | a third failure would be a regression | planned |
| AC8 | integration | `gh pr checks --watch` | verify, backend, frontend, docker-build, sonarcloud, CodeQL green | n/a | a red check blocks the merge | planned |

## Regression risk

The only behaviour that can change is the factory's own tooling and CI (`verify.py` is new, the factory-verify workflow
runs it). The application and its tests do not change; the baseline of 2 known failures must hold.

## Untestable AC

None.

## Manual checks

AC6: for each of the new tickets and ADE-14, 16, 17, 18, 20, 21, 32, 33, 42, 65, 74 read the issue in Jira; confirm the
four parked tickets show the label `parked` and their status is unchanged.

## Audit (after implementation)

To be filled after the checks are run.
