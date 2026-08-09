---
id: BLK-106
type: feature
title: "Add width — new document types beyond the initial 12"
priority: medium
status: done
started: 2026-08-08T15:50:00+05:30
completed: 2026-08-08T16:20:00+05:30
phase: 4
owner: backend
created: 2026-08-08T03:30:00+05:30
estimate: L
depends-on: [BLK-103, BLK-105]
tags: [backend, skills, templates, width, new-document-types]
---

## Description

Add new document types to expand the platform's coverage beyond
the initial 12. Each new type needs: skill + template + prebuilt
definition + sample data + tests.

## New Document Types (priority order)

### Tier 1 — Common business documents (high value, easy to source)

| # | Document Type | Sector | Why | Complexity |
|---|--------------|--------|-----|------------|
| 1 | Bank Statement | Financial | Transaction tables, running balances | Medium |
| 2 | Purchase Order | B2B | Header + line items, matches invoice pattern | Low |
| 3 | Packing List | Logistics | Tabular, multi-page | Low |
| 4 | W-2 Tax Form | Tax | Fixed layout, OCR-friendly | Low |
| 5 | Pay Stub | HR | Tabular, deductions | Medium |
| 6 | Insurance Policy Declaration | Insurance | Multi-page, structured | Medium |

### Tier 2 — Industry-specific (medium value, harder to source)

| # | Document Type | Sector | Why | Complexity |
|---|--------------|--------|-----|------------|
| 7 | Customs Declaration | Trade | Structured form, codes | Medium |
| 8 | Material Safety Data Sheet (MSDS) | Chemical | Sections, tables | Medium |
| 9 | Nutrition Label | Food | Fixed format, small | Low |
| 10 | Inspection Certificate | QA | Checklist + measurements | Low |

### Tier 3 — Complex / niche (lower priority)

| # | Document Type | Sector | Why | Complexity |
|---|--------------|--------|-----|------------|
| 11 | Patent Application | Legal | Multi-section, dense text | High |
| 12 | Clinical Trial Report | Pharma | Tables, statistics | High |
| 13 | Environmental Impact Report | Govt | Multi-page, mixed format | High |

## Per-Type Deliverable

For each new document type:
1. **Template** — Pydantic schema with fields, types, thresholds
2. **Skill** — System prompt, probe order, invariants, failure actions
3. **Prebuilt definition** — Agent definition wiring skill + template + tools
4. **Sample data** — 2-3 sample documents in `sample-data/`
5. **Tests** — Structure tests + invariant tests + e2e smoke test

## Acceptance Criteria

- [x] Tier 1 (6 types) implemented with full skill/template/definition
- [ ] Each new type has 2+ sample documents (deferred — sample data not included in this PR)
- [x] Each new type has structure + invariant tests
- [ ] E2E smoke test for each new type (deferred — requires sample documents)
- [x] Prebuilt definitions registered in run engine
- [x] No regression in existing tests (893 total)

## Notes

- Start with Tier 1 only — these are the most common document types
  and will demonstrate platform breadth
- Tier 2 and 3 are Phase 5+ items
- Bank Statement template already exists in the catalogue — verify
  it works with real sample data before adding new types
