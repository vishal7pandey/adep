---
id: BLK-041
type: feature
title: "Multi-page hierarchical state — DocumentState / PageState / RegionState"
priority: high
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T22:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-008, BLK-039]
tags: [agent, state, multi-page, hierarchical, scaling, real-estate, legal]
---

## Description

Extend AgentState with a hierarchical document model:
`DocumentState → PageState[] → RegionState[]`. Instead of a flat region
index, the agent navigates a tree: document contains pages, pages contain
regions, regions contain extracted values. This bounds context for
multi-page documents (60-page leases, 100-page compliance audits).

## Motivation

DocVQA benchmarks (MP-DocVQA, DUDE) show VLM accuracy degrades
significantly on multi-page documents due to context dilution. ADE
solves this through hierarchical state + field-driven working sets:
the agent's plan node evaluates the region index and generates a focused
working set, using `crop` to materialize only relevant pages/regions.

ADE industry mapping: §Sector 4 (Real Estate — 60-page commercial leases),
§Sector 3 (IT compliance — 100-page SOC 2 reports).

## Acceptance Criteria

- [ ] `PageState` dataclass: page_number, regions (dict), status, fields_extracted
- [ ] `DocumentState` dataclass: pages (list[PageState]), total_pages, current_page
- [ ] AgentState extended with `document_state: DocumentState`
- [ ] `detect_layout` populates PageState for each page
- [ ] Plan node navigates hierarchy: "go to page X, region Y"
- [ ] `crop` tool accepts page + region coordinates
- [ ] Field-driven working set: plan node selects only relevant pages for current gaps
- [ ] Trace compaction preserves page-level extraction state
- [ ] SSE events include `page` field for all tool calls
- [ ] Unit tests: 5-page document extraction with page-aware navigation
- [ ] Integration test: 20-page document, agent navigates to correct pages

## Constraints

- State carries handles, not pixels [§2.7] — PageState stores region metadata only
- Must work with existing compact_trace rolling window [§12.3]
- Backward compatible: single-page documents work as before (1 PageState)

## Dependencies

- BLK-008 (ReAct graph — plan node needs hierarchy awareness)
- BLK-039 (Compaction — must preserve page-level state)

## Notes

- ADE industry mapping: §Sector 4 (Real Estate), §Sector 3 (IT Compliance)
- vision.md §12.1 (hierarchical locate), §12.2 (field-driven working set)
- MP-DocVQA, DUDE benchmarks for multi-page evaluation
