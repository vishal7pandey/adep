---
id: BLK-042
type: feature
title: "Industry Skill Library — sector-specific skills for GICS industries"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T22:30:00+05:30
started: null
completed: null
estimate: XL
depends-on: [BLK-011, BLK-040, BLK-041]
tags: [skills, industry, trade-finance, construction, compliance, medical, energy]
---

## Description

Build a library of sector-specific Skills mapped to the GICS 11-sector
MECE framework. Each skill encodes domain expertise: probe order, tool
preferences, mathematical invariants, failure actions, and semantic
checks tailored to the document types in that sector.

## Sector → Skill Mapping

| Sector | Skill Name | Key Documents | Key Invariants |
|--------|-----------|---------------|----------------|
| Financials | TradeFinanceScrutinySkill | MT700, BoL, invoices | Date arithmetic, amount tolerance, document coverage |
| Industrials | BillOfQuantitiesSkill | BOQ, engineering specs | qty × rate = total, VAT consistency |
| IT | ComplianceAuditSkill | SOC 2, OSPAR, MAS TRM | Boolean control checks, encryption standards |
| Real Estate | CommercialLeaseSkill | Lease agreements | CAM fee structure, rent escalation |
| Energy | CommodityTradeSkill | Assay reports, BoL | Volumetric tolerance bands, API gravity |
| Materials | MetallurgicalAssaySkill | MSDS, assay certs | Composition matrix, OCR→VLM fallback |
| Health Care | MedicalClaimSkill | CMS-1500, UB-04 | ICD-10 cross-checks, demographic logic |
| Consumer Disc. | StoreAuditSkill | Audit reports, photos | Visual evidence cross-reference |
| Consumer Staples | ThermalReceiptSkill | Thermal receipts, POS | subtotal + tax = total, geometry-first probe |
| Communication | AdBuySkill | Insertion orders | Local tiers sum to national total |
| Utilities | UtilityBillSkill | Utility bills | Chart extraction (read_chart), consumption history |

## Acceptance Criteria

- [ ] At least 3 skills implemented in Phase 4: TradeFinance, BillOfQuantities, UtilityBill
- [ ] Each skill has: system_prompt, tool_prefs, probe_order, invariants, failure_actions
- [ ] Each skill has a corresponding Template (schema contract)
- [ ] TradeFinanceScrutinySkill: MT700 field extraction + deterministic date/amount checks
- [ ] BillOfQuantitiesSkill: table extraction + qty×rate=total invariant
- [ ] UtilityBillSkill: read_chart integration for consumption history
- [ ] Each skill tested with sample documents from its domain
- [ ] Skills registered in Definition Store for frontend selection

## Constraints

- VLMs handle perception; deterministic code handles math/dates/coverage [§4]
- Prompt injection defense: LLM never issues final verdict — validator does
- Each skill's failure actions specify crop→deskew→VLM fallback for degraded scans
- Skills are data (Python dataclasses), not code-heavy [SF]

## Dependencies

- BLK-011 (InvoiceSkill — pattern to follow)
- BLK-040 (read_chart — needed by UtilityBillSkill)
- BLK-041 (hierarchical state — needed by CommercialLease, ComplianceAudit)

## Notes

- ADE industry mapping: full GICS sector analysis
- Start with 3 highest-value skills; expand library incrementally
- Each skill pair (skill + template) = one Agent Definition
