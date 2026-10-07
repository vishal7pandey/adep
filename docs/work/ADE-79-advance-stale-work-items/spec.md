# ADE-79 — Advance stale work items

Status: draft · Risk: low · Jira: ADE-79
Created: 2026-10-07 · Slug: advance-stale-work-items

## Problem

`factory status` still lists ADE-26 and ADE-55 as `in-review` ("human: merge the PR") although their pull requests (#22 and
#23) were merged on 2026-10-06, and it lists ADE-30 as `spec-approved` with `pr: null` although its docs-only PR #7 was
merged on 2026-10-05. The status table is the owner's inbox for open work; stale rows hide the real open items and make the
table untrustworthy. PR #22 itself advanced 17 other items but could not advance its own item (a PR cannot know its merge
before it merges) and PR #23 had the same gap.

## Users and context

The owner and the agents, who read `factory status` to see what is open. Grounded in: `factory status` on master (ef900ae),
every `docs/work/*/item.yaml` on master 60d4d98 (33 items before this one; 29 `merged`, ADE-26 and ADE-55 `in-review`,
ADE-30 `spec-approved`, ADE-77 `in-review` for PR #46 which just merged), `gh pr view <n> --json state,mergedAt` for #22, #23 and #7, and `docs/work/ADE-30-engine-vertical-slice/spec.md`
(which says the item is a design reference that "does not get a plan.md or an implementation").

## Goals and non-goals

**Goals**
- Every work item whose pull request is MERGED has status `merged` and `pr` recorded as a string.
- `factory status` shows no `in-review` row for a merged PR.

**Non-goals**
- No Python or frontend code change, no change to any spec, plan or test plan other than the audit note of ADE-77.
- No release or `done` transitions (those belong to `factory-release`).
- No change to an item whose PR is open or whose evidence is unclear.

## Requirements

- R1. Each item with status `in-review` whose PR is MERGED on GitHub must be advanced with `factory advance <ID> merged --pr <n>`.
- R2. ADE-30 (spec-approved, `pr: null`) is set to `merged` with `pr: '7'` only if the factory accepts it: PR #7 contains exactly
  its `item.yaml` and `spec.md` (docs only) and is MERGED, its own spec states it is a design reference without plan or
  implementation, all seven children (ADE-34 to ADE-40) are `merged` and Jira ADE-30 is Done. If the factory's own checks
  reject the change (a skip from `spec-approved`, or `verify.py` demanding an approved plan and a test plan), the evidence is
  not clear within the method, and ADE-30 is left alone and reported to the owner.
- R3. `pr` stays a string in every touched `item.yaml`.
- R4. ADE-77 (this chain's previous item, PR #46 merged) and ADE-79 itself are advanced to `merged`, so the table is clean
  after this PR merges.

## Acceptance criteria

- AC1. (R1, R3) After the change `docs/work/ADE-26-*/item.yaml` has `status: merged`, `pr: '22'` and `docs/work/ADE-55-*/item.yaml`
  has `status: merged`, `pr: '23'`; for every item in `docs/work/*/item.yaml` whose `pr` is MERGED on GitHub, `status` is
  `merged` (checked with a loop over `gh pr view <n> --json state`).
- AC2. (R2, R3) Either ADE-30 has `status: merged` and `pr: '7'` and `verify.py` passes, or (if `factory advance` or
  `verify.py` refuses) the item is byte-for-byte unchanged and the reason is reported.
- AC3. (R4) ADE-77 and ADE-79 have `status: merged` with `pr: '46'` and the PR number of this change.
- AC4. (R1) `python .factory/verify.py` prints `verify: OK`, `factory sync --check .` exits 0, and `factory status` lists no
  `in-review` work item for a merged PR (only the dependency and decision summaries, plus ADE-30 if it was left alone).
- AC5. (failure path) An item whose PR is still OPEN is not touched: none exists today; the loop in AC1 must report it as
  "open, left alone" rather than advancing it.

## Edge cases and failure modes

- A PR number recorded as a URL (ADE-63 holds `https://github.com/vishal7pandey/adep/pull/25`) is already `merged`; left as it is.
- If `factory advance` rejects a one-step-forward rule for ADE-30, no hand edit is made unless it is a minimal status/pr edit that
  `verify.py` accepts; otherwise ADE-30 stays and is reported.

## Non-functional requirements

- Policy: `.factory/policies/git.md` (branch, PR, human gates); no secret is read or written.

## Assumptions

- Merged PRs imply the work is merged; whether the change is released is out of scope here.
- Jira ADE-30 being Done (Confluence change log, 2026-10-05) is accepted as evidence together with the merged PR and children.

## Risks and dependencies

Low risk: metadata only, reversible by revert. Depends on `gh` read access to the PR states.
