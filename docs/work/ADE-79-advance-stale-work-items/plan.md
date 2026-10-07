# ADE-79 — Advance stale work items

Status: draft · Risk: low · Jira: ADE-79
Created: 2026-10-07 · Slug: advance-stale-work-items · Spec: spec.md

## Summary

Run `factory advance <ID> merged --pr <n>` for the stale items found by a loop over all `docs/work/*/item.yaml` and the PR
states from `gh`, set ADE-30 only if the factory accepts it, and advance ADE-77 and ADE-79 themselves.

**Size:** S

## Current state

`docs/work/*/item.yaml` hold `status` and `pr`. `factory status` and `.factory/verify.py` read them. Stale today: ADE-26
(in-review, pr '22'), ADE-55 (in-review, pr '23'), ADE-30 (spec-approved, pr null). Commands: `factory advance`,
`python .factory/verify.py`, `factory sync --check .`, all through `C:/Dev/ai-software-factory/.venv` with
`PYTHONPATH=C:/Dev/ai-software-factory/src`.

## Approach

1. List every item whose status is not `merged` or later and look up the PR state with `gh pr view <n> --json state`.
2. Advance ADE-26 and ADE-55 with the CLI. Try ADE-30 with the CLI; if it refuses, a minimal edit of `status` and `pr`
   (only if `verify.py` passes), else leave it and report.
3. Fill the ADE-77 audit note for AC3 (alert 8 `fixed`), advance ADE-77, then ADE-79 itself just before the merge (the same
   way as ADE-75).
4. `verify.py`, `sync --check .`, `factory status`.

**Alternatives rejected:** editing the YAML by hand for the CLI-supported transitions (the CLI keeps the format);
leaving the stale rows for the owner (the table exists to be believed).

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Inventory of non-merged items and their PR states | none | AC1, AC5 | listing |
| T2 | Advance ADE-26 and ADE-55 | their `item.yaml` | AC1 | `status: merged`, `pr: '22'` / `'23'` |
| T3 | ADE-30 decision and edit | `docs/work/ADE-30-*/item.yaml` | AC2 | `merged`, `pr: '7'`, or left with reason |
| T4 | ADE-77 audit note and advance; ADE-79 advance | their work item files | AC3 | `status: merged` |
| T5 | Checks and CI incl. CodeQL and sonarcloud | none | AC4 | `verify: OK`, `sync --check` 0, empty status table, CI green |

## Data, API and migration impact

None (work-item metadata only).

## Security and failure modes

No secret, no code. A wrong advance is a one-line revert.

## Rollout and rollback

Merge via PR; revert the merge commit to undo.

## Risks and open points

`verify.py` may require a plan or test plan for an item at `merged` (ADE-30 has none by design); then ADE-30 stays and is
reported to the owner.
