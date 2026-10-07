# ADE-79 — Test plan: Advance stale work items

Status: draft · Risk: low · Jira: ADE-79

Test framework and conventions found: no automated tests apply (metadata only, no code). The checks are the factory's own:
`python .factory/verify.py`, `factory sync --check .`, `factory status`, plus a loop over `docs/work/*/item.yaml` and
`gh pr view <n> --json state`. Every AC is checked by command (Level manual: the CLI output is the evidence, there is nothing to unit test).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | manual | loop over `docs/work/*/item.yaml` with `gh pr view <n> --json state` | every item with a MERGED PR is `merged`, ADE-26 `pr: '22'`, ADE-55 `pr: '23'` | `pr` stays a string; ADE-63 holds a URL and is already merged | an item with an OPEN PR is reported, not advanced (none exists) | verified |
| AC2 | manual | `factory advance ADE-30 merged --pr 7` then `verify.py` | ADE-30 `merged`, `pr: '7'` | n/a: single item | if the CLI or verify refuses, the item is unchanged and the reason reported | verified |
| AC3 | manual | `factory advance ADE-77 merged --pr 46`, `factory advance ADE-79 merged --pr <n>` | both `merged`, pr string | n/a: two items | n/a: no failure path | verified |
| AC4 | manual | `python .factory/verify.py`; `factory sync --check .`; `factory status` | `verify: OK`, exit 0, no work-item row | n/a: command-level | a leftover `in-review` row would show in `factory status` | verified |
| AC5 | manual | the same loop, open-PR branch | n/a: no open item exists | n/a | the loop prints "open, left alone" for any open PR (ADE-79 itself at the first run) | verified |

## Regression risk

Only `item.yaml` metadata changes (plus the ADE-77 audit note). No code, so the Python and frontend suites cannot change; CI
runs them anyway. `verify.py` is the check that an advanced item is consistent.

## Untestable AC

None.

## Manual checks

All rows above: the commands and their output are recorded under Audit.

## Audit (after implementation)

AC1, AC5: a loop over every `docs/work/*/item.yaml` with `gh pr view <n> --json state` found exactly three items whose PR is
MERGED but whose status was not `merged`: ADE-26 (PR 22), ADE-55 (PR 23), ADE-77 (PR 46). Every other item with a PR was
already `merged` with the PR MERGED; no item has an OPEN PR (`gh pr list --state open` was empty), so the "left alone" branch
had nothing to act on. After `factory advance <ID> merged --pr <n>` the three read `merged`, `pr` a string.

AC2: `factory advance ADE-30 merged --pr 7` was refused (`cannot skip from spec-approved to merged; next status is
plan-approved`). A minimal hand edit (`status: merged`, `pr: '7'`) was tried and `verify.py` rejected it with three FAIL lines
(`approvals.plan` missing, `plan.md` and `test-plan.md` missing or empty), so the edit was reverted: ADE-30 is unchanged
(`git diff` empty) and is reported to the owner: the factory has no way to record a finished design-reference item without
a plan, and inventing a plan approval would be false.

AC3: ADE-77 advanced with `--pr 46`; ADE-79 advanced to `merged` with its own PR number just before the merge.

AC4: `verify: OK`; `factory sync --check .` printed `in sync with the factory source`, exit 0; `factory status` lists no
`in-review` item (only ADE-30 as `spec-approved`, ADE-79 until it merges).
