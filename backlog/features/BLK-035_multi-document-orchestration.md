---
id: BLK-035
type: feature
title: "Multi-document orchestration (v2, L9 territory)"
priority: low
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: XL
depends-on: []
tags: [multi-doc, orchestration, v2, scaling]
---

## Description

Per-document extraction produces per-doc ExtractedResults. A separate
cross-doc validator graph operates over those results (the "same applicant"
check from L9), never over pixels. Cross-doc validation is a different layer
sitting above the per-doc loop, not a modification of it.

## Acceptance Criteria

- [ ] Cross-doc validator graph
- [ ] Document package model (collection of documents + cross-doc rules)
- [ ] API endpoint for multi-doc runs
- [ ] Frontend support for document packages

## Dependencies

- Phase 1-3 complete

## Notes

- vision.md §12.5 (Multi-Document Orchestration)
