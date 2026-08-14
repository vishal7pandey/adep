---
id: BLK-185
type: bug
title: "Run metadata contract drift breaks rename, search, duplicate, export, and preview flows"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T10:15:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [backend, frontend, api, metadata, runs, preview, analytics]
---

## Description

The run model mixes `document_url`, `document_path`, document IDs, page-image paths, and a separate `name` field without a canonical contract. Different endpoints and frontend components read and write different keys, which causes session metadata to decay as soon as runs are renamed, duplicated, exported, previewed, or launched from uploaded documents.

## Problem Statement

Observed inconsistencies include:

- `src/api/run_engine.py` serializes runs with `document_url`
- `src/api/routes/runs.py` duplicates and exports using `document_path`
- run search filters on `document_path`, not `document_url` or `name`
- the rename endpoint writes `name`, but `frontend/components/layout/Sidebar.tsx` renders and mutates `document_url` instead
- uploaded documents are converted to `page_paths[0]` before `startExtractionRun()`, so the run loses the document ID and original document identity
- preview logic expects a real filesystem path, which is incompatible with runs that only retain logical document references

This leads to user-visible breakage:

- renamed sessions do not have a consistent source of truth
- duplicated runs can lose their document reference
- exported JSON omits the actual document key for many runs
- run search misses renamed or current-format records
- analytics derive document type from unstable path strings
- preview behavior depends on whether the run happened to store a page path or some other value

## Acceptance Criteria

- [ ] Define one canonical run metadata contract for source document identity and display name
- [ ] Duplicate/export/search/preview all read the same canonical fields
- [ ] Rename updates a display-name field that the backend and frontend both honor
- [ ] Uploaded-document runs preserve the logical document ID alongside any derived page/image path
- [ ] Analytics derive document categorization from stable metadata rather than ad hoc path parsing
- [ ] API and frontend tests cover rename, duplicate, export, and preview with both filesystem-backed and document-store-backed runs

## Constraints

- Maintain backward compatibility for older run records where feasible
- Do not require destructive migration of existing `.adep/runs/*.json` files
- Provide a compatibility layer or normalization step for mixed historical records

## Dependencies

- Likely touches `src/api/run_engine.py`, `src/api/routes/runs.py`, `frontend/lib/api.ts`, `frontend/lib/analytics.ts`, `frontend/components/layout/Sidebar.tsx`, and `frontend/components/workbench/Pane1AgentConsole.tsx`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
