---
id: BLK-104
type: feature
title: "Expand sample data — cover all 12 document types with 2-3 samples each"
priority: medium
status: backlog
phase: 3
owner: mgmt
created: 2026-08-08T03:30:00+05:30
estimate: S
depends-on: []
tags: [mgmt, sample-data, testing, width]
---

## Description

Download or generate sample documents for all 12 document types
covered by the prebuilt catalogue. Currently 7 files across 5
categories. Need to fill the remaining 7 categories and add more
samples to existing categories.

## Current State

| Category | Samples | Status |
|----------|---------|--------|
| invoices | 2 PDFs | ✅ done |
| bank-statements | 1 PDF | needs 1 more |
| contracts | 1 PDF | needs 1 more |
| utility-bills | 1 PDF | needs 1 more |
| medical-claims | 2 PDFs | ✅ done |
| boq | 1 PDF | needs 1 more |
| receipts | 0 | needs 2-3 |
| leases | 0 | needs 2 |
| compliance-audits | 0 | needs 2 |
| trade-finance | 0 | needs 2 |
| commodity-trade | 0 | needs 2 |
| metallurgical-assay | 0 | needs 2 |
| store-audits | 0 | needs 2 |
| ad-buy | 0 | needs 2 |

## Sources

- **Receipts**: ExpressExpense free dataset (200 images, MIT license)
  or generate via DeskRated receipt generator
- **Leases**: LegalTemplates.net or Jotform free PDF template
- **Compliance audits**: Generate synthetic audit report PDF
- **Trade finance**: Generate synthetic letter of credit
- **Commodity trade**: Generate synthetic trade confirmation
- **Metallurgical assay**: Generate synthetic assay certificate
- **Store audits**: Generate synthetic store audit checklist
- **Ad buy**: Generate synthetic insertion order

## Acceptance Criteria

- [ ] All 14 categories have at least 2 sample documents
- [ ] `sample-data/README.md` updated with full inventory
- [ ] File sizes > 0 (no corrupt downloads)
- [ ] Mix of PDF and image formats where possible
