---
id: BLK-292
type: bug
title: "Parallel audit processes created duplicate BLK-IDs — backlog integrity compromised"
priority: high
status: backlog
phase: 5
owner: mgmt
created: 2026-08-09T11:30:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [process, backlog, mgmt, audit, governance]
---

## Description

Two independent audit passes ran concurrently against the same repo and both assigned BLK-IDs from the same sequence (starting at BLK-177). The result is a large set of **duplicate BLK-IDs** pointing to different files:

| ID | File A (this audit) | File B (parallel audit) |
|----|---------------------|--------------------------|
| BLK-177 | adep-directory-missing-from-gitignore | ready-endpoint-misreports-provider-readiness |
| BLK-178 | makefile-references-deleted-requirements-dev | pdf-fallback-bypasses-react-agent |
| BLK-180 | docker-compose-references-missing-frontend-dockerfile | duplicate-non-communicating-circuit-breakers |
| BLK-181 | path-prefix-scope-match-overly-broad | skill-template-registry-manual-duplication |
| BLK-182 | pane2-shows-sample-pid-graph-tab-for-all-definitions | unwired-eval-benchmarks-accuracy-modules |
| BLK-183 | frontend-env-and-cors-config | decorative-prompt-injection-detector |
| BLK-184 | frontend-tests-use-real-network-calls | pause-resume-lifecycle-is-not-actually-resumable |
| BLK-185 | workbench-context-uses-datenow-runid | run-metadata-contract-drift-breaks-rename-search-duplicate-and-preview |
| BLK-186 | frontend-document-search-and-pagination | bootstrap-admin-secret-is-written-to-logs |
| BLK-187 | webhook-delivery-retry-and-dashboard | frontend-run-state-model-collapses-distinct-backend-outcomes |
| BLK-188 | bootstrap-admin-key-logged-in-plaintext | partial-runs-are-counted-as-success-across-analytics |
| BLK-189 | detect-tables-tool-missing | replace-deprecated-lifecycle-hooks-and-stale-test-runtime-apis |
| BLK-190 | local-first-clipboard-and-filename-export | redundant-opencv-installs-oversized-requirements |
| BLK-191 | llm-silent-failure-returns-empty-content | runtime-artifacts-committed-to-git |
| BLK-192 | unbounded-run-context-memory-growth | backlog-tickets-not-closed-when-fixed |
| BLK-193 | rate-limit-disabled-by-default-in-production | frontend-dockerfile-missing |

This breaks the backlog's referential integrity: `depends-on`, `STATUS.md`, and `comms` references to a BLK-ID are now ambiguous. It also makes it impossible to track which item was actually completed.

## Root Cause

No central ID allocation mechanism (e.g. a lock file, a "next BLK-ID" counter, or a reservation step) was in place before the audit started. Both processes read the max existing ID (176) and started allocating from 177 independently.

## Acceptance Criteria

- [ ] A single source of truth for the next BLK-ID is established (e.g. `projectmgmt/NEXT-BLK-ID` file or a reserved range)
- [ ] All duplicate IDs are renumbered so each BLK-ID is unique
- [ ] `STATUS.md` and `comms` references are updated to the renumbered IDs
- [ ] A process note is added to `PROCESS.md` requiring ID reservation before creating backlog items
- [ ] No two files in `backlog/` share the same BLK-ID

## Constraints

- Must not lose any of the audit findings — renumber, don't delete
- The renumbering must be coordinated by mgmt

## Dependencies

- None

## Notes

- This is a governance/process failure, not a code failure
- Many findings overlap between the two audits (e.g. both found the Makefile requirements-dev issue, both found the bootstrap key logging, both found the missing frontend Dockerfile) — these should be deduplicated during renumbering
- Related to `projectmgmt/PROCESS.md` and `projectmgmt/audit-ledger.md`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `mgmt` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
