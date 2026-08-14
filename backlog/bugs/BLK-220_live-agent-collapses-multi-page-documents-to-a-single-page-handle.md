---
id: BLK-220
type: bug
title: "Live agent collapses multi-page documents to a single-page handle"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T11:15:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [agent, documents, multi-page, runtime, pdf, wiring]
---

## Description

The document ingestion layer supports multi-page PDFs and TIFFs, and the classification path can consume `page_paths`. The live extraction loop does not. `build_initial_state()` hardcodes the runtime document handle to one page with a single page path derived from the input path.

## Problem Statement

`src/run.py:build_initial_state()` currently constructs:

- `pages=1`
- `page_paths=[document_path]`

That discards the multi-page structure already available elsewhere in the system.

This breaks the agentic runtime contract in several ways:

- the planner cannot reason over actual page count
- tools cannot reliably iterate per-page through the state model
- uploaded documents often get reduced to `page_paths[0]` before starting a run, which strips the rest of the document from the live execution context
- multi-page classification exists, but multi-page extraction state does not

The result is that the platform supports multi-page documents operationally, but the live agent loop behaves like a single-page agent with ad hoc workarounds.

## Acceptance Criteria

- [ ] `build_initial_state()` receives and preserves true page count and page paths
- [ ] Run startup preserves logical document identity plus full page list for document-store-backed uploads
- [ ] Agent tools that need page iteration can read the real multi-page handle from state
- [ ] Multi-page extraction tests cover a document where page 2+ is required for completion
- [ ] UI/runtime docs stop implying multi-page agent support unless the full live path actually supports it

## Constraints

- Preserve support for direct filesystem single-image runs
- Avoid coupling the agent state too tightly to one storage backend
- Coordinate with preview/export/run metadata normalization so page identity stays consistent

## Dependencies

- `src/run.py`
- `src/api/run_engine.py`
- `frontend/components/workbench/Pane1AgentConsole.tsx`
- `src/documents/store.py`
- any tools that should consume `state.document.page_paths`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
