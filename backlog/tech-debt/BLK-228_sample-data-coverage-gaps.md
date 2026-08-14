---
id: BLK-228
type: tech-debt
title: "25 sample-data subdirectories but only some have actual sample files — inventory mismatch with 22+ skills"
priority: low
status: backlog
phase: 2
owner: mgmt
created: 2026-08-09T14:00:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [sample-data, testing, fixtures, coverage]
---

## Description

The `sample-data/` directory has 25 subdirectories for different document types. The `README.md` documents the expected inventory per folder. However, the prebuilt catalogue defines 22+ skills/templates. Some sample folders may be empty or have mismatched content relative to the skills that depend on them.

The `SOURCE-MAP.md` (7KB) provides a curated source catalog, but there's no automated verification that the sample data actually covers all skills, or that the samples are valid PDFs/images that can be processed by the extraction pipeline.

## Problem Statement

- No automated check verifies that each skill has corresponding sample data
- The e2e tests use `def-trade-finance-scrutiny` for invoice tests (BLK-208) — the sample data may not align with the definitions used in tests
- Some sample folders may be empty (the directory listing shows 0 items for some, though this may be due to `.gitignore` or binary files)
- The integration tests (`test_integration_real.py`) skip when providers aren't configured, so sample data coverage is never verified in CI
- New document types added to the prebuilt catalogue may not have corresponding sample data, and nothing alerts anyone to the gap

## Acceptance Criteria

- [ ] Write a script that cross-references prebuilt skills/templates with `sample-data/` subdirectories and reports missing or empty folders
- [ ] Add this check to CI as a non-blocking warning
- [ ] Ensure every prebuilt skill has at least 2 sample documents
- [ ] Verify all sample files are valid (openable by PyMuPDF or PIL)

## Constraints

- Don't require sample data for skills that are in `backlog/features/` (not yet implemented)
- The check should be informational, not a CI failure

## Dependencies

- `sample-data/` directory
- `src/definitions/prebuilt.py` (skill/template catalogue)
- Related to BLK-208 (e2e tests use wrong definition) and BLK-209 (fake PDF fixture)

## Notes

- Found during full-repo audit; the sample data collection is impressive in scope but lacks automated verification

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `mgmt` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
