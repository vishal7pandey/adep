---
id: BLK-087
type: feature
title: "Prebuilt catalogue — 11 GICS sector agents, skills, and templates"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T02:00:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-016, BLK-017, BLK-042]
tags: [backend, catalogue, prebuilt, agents, skills, templates, gics, industry]
---

## Description

Implement a full catalogue of prebuilt agent definitions, skills, and
templates covering all 11 GICS sectors identified in the ADE Industry
Mapping document. Each sector has a specific document archetype with
unique extraction challenges, invariants, and tool preferences.

## Current State

**Implemented (4 skills, 4 templates, 0 prebuilt definitions):**
- Skills: `invoice`, `trade_finance`, `bill_of_quantities`, `utility_bill`, `vlm_fallback`
- Templates: `invoice`, `trade_finance`, `bill_of_quantities`, `utility_bill`
- Prebuilt agent definitions: none

**Missing (7 skills, 7 templates, 11 agent definitions):**

## Full Catalogue

### Sector 1: Financials — Trade Finance Scrutiny

**Skill:** `TradeFinanceScrutinySkill` (exists — review & harden)
**Template:** `trade_finance_mt700` (exists — review & harden)
**Agent Definition:** `def-trade-finance-scrutiny`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| field_32B_currency | string | MT700 | — |
| field_32B_amount | float | MT700 | invoice_amount ≤ 32B + tolerance |
| field_44C_latest_shipment | date | MT700 | BoL on-board date ≤ 44C |
| field_45A_goods_description | text | MT700 | invoice desc semantically matches |
| field_46A_required_documents | list | MT700 | coverage: all docs exist in presentation |
| field_47A_additional_conditions | text | MT700 | detect logical traps; manual review trigger |
| presentation_compliance | boolean | derived | all invariants pass |

**Tools:** `detect_layout`, `ocr`, `vlm`, `cross_check`, `crop_image`
**Key challenge:** Field 47A free-text interpretation; date arithmetic
must be deterministic (never LLM).
**Max iterations:** 25 (complex multi-document)

### Sector 2: Industrials — Bill of Quantities

**Skill:** `BillOfQuantitiesSkill` (exists — review & harden)
**Template:** `bill_of_quantities` (exists — review & harden)
**Agent Definition:** `def-boq-estimator`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| line_items[] | table | BOQ table | unit_qty × unit_rate = line_total |
| project_name | string | header | — |
| contractor | string | header | — |
| total_direct_cost | float | derived | sum(line_items) |
| overhead_percentage | float | BOQ | — |
| vat_amount | float | BOQ | VAT consistency across all items |
| grand_total | float | derived | total_direct + overhead + contingency + VAT |

**Tools:** `detect_layout`, `detect_tables`, `ocr`, `read_table`, `crop_image`, `cross_check`
**Key challenge:** Multi-page dense tabular data; exact match for numbers.
**Max iterations:** 30 (thousands of rows)

### Sector 3: Information Technology — Compliance Audit

**Skill:** `ComplianceAuditSkill` (NEW)
**Template:** `compliance_audit_soc2` (NEW)
**Agent Definition:** `def-compliance-audit`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| encryption_at_rest | boolean | SOC 2 | AES-256 confirmed |
| encryption_in_transit | boolean | SOC 2 | TLS 1.3 confirmed |
| access_controls | boolean | SOC 2 | — |
| penetration_testing | boolean | SOC 2 | annual cadence |
| data_isolation | boolean | SOC 2 | tenant isolation confirmed |
| audit_log_retention | integer | SOC 2 | ≥ 365 days |
| outsourcing_registered | boolean | OSPAR | — |
| control_count_total | integer | doc | — |
| control_count_passed | integer | derived | — |

**Tools:** `detect_layout`, `ocr`, `vlm`, `locate`, `crop_image`
**Key challenge:** Hundred-page documents; hierarchical navigation needed.
**Max iterations:** 40

### Sector 4: Real Estate — Commercial Lease Abstraction

**Skill:** `CommercialLeaseSkill` (NEW)
**Template:** `commercial_lease` (NEW)
**Agent Definition:** `def-commercial-lease`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| landlord | string | header | — |
| tenant | string | header | — |
| premises_address | string | clauses | — |
| lease_term_months | integer | clauses | — |
| commencement_date | date | clauses | — |
| expiration_date | date | clauses | commencement + term |
| base_rent_monthly | float | clauses | — |
| rent_escalation_pct | float | clauses | — |
| cam_fees | text | clauses | — |
| security_deposit | float | clauses | — |
| renewal_option | boolean | clauses | — |
| termination_clause | text | clauses | — |

**Tools:** `detect_layout`, `ocr`, `vlm`, `locate`, `crop_image`
**Key challenge:** 60+ page documents; context dilution; field-driven
working set with hierarchical state.
**Max iterations:** 35

### Sector 5: Energy — Commodity Trade Reconciliation

**Skill:** `CommodityTradeSkill` (NEW)
**Template:** `commodity_trade_assay` (NEW)
**Agent Definition:** `def-commodity-trade`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| commodity_type | string | assay | — |
| loaded_volume_barrels | float | BoL | within ±5% of LC tolerance |
| loaded_volume_metric_tons | float | assay | — |
| api_gravity | float | assay | — |
| temperature_observed | float | assay | — |
| volume_at_15c | float | derived | temperature correction applied |
| vessel_name | string | BoL | matches across all docs |
| loading_port | string | BoL | matches LC Field 44E |
| discharge_port | string | BoL | matches LC Field 44F |
| inspector_company | string | assay | — |

**Tools:** `detect_layout`, `ocr`, `vlm`, `read_table`, `cross_check`, `crop_image`
**Key challenge:** Volumetric reconciliation across multiple documents;
temperature corrections.
**Max iterations:** 20

### Sector 6: Materials — Metallurgical Assay

**Skill:** `MetallurgicalAssaySkill` (NEW)
**Template:** `metallurgical_assay` (NEW)
**Agent Definition:** `def-metallurgical-assay`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| certificate_number | string | header | — |
| material_grade | string | header | — |
| composition_elements[] | table | assay table | each element within spec range |
| composition_values[] | table | assay table | — |
| spec_min[] | table | assay table | value ≥ spec_min |
| spec_max[] | table | assay table | value ≤ spec_max |
| heat_number | string | header | — |
| test_date | date | header | — |
| inspector | string | footer | — |

**Tools:** `detect_layout`, `detect_tables`, `ocr`, `read_table`, `vlm`, `crop_image`, `deskew`
**Key challenge:** Low-quality scans from remote sites; OCR fallback to
VLM for degraded dot-matrix print.
**Max iterations:** 20

### Sector 7: Health Care — Medical Claims

**Skill:** `MedicalClaimSkill` (NEW)
**Template:** `medical_claim_cms1500` (NEW)
**Agent Definition:** `def-medical-claim`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| patient_name | string | CMS-1500 | — |
| patient_dob | date | CMS-1500 | — |
| patient_gender | string | CMS-1500 | gender/procedure consistency |
| provider_npi | string | CMS-1500 | 10-digit NPI format |
| provider_name | string | CMS-1500 | — |
| diagnosis_codes[] | list | CMS-1500 | ICD-10 format valid |
| procedure_codes[] | list | CMS-1500 | CPT format valid |
| service_date_from | date | CMS-1500 | — |
| service_date_to | date | CMS-1500 | from ≤ to |
| billed_amount | float | CMS-1500 | sum of line items |

**Tools:** `detect_layout`, `ocr`, `vlm`, `crop_image`, `cross_check`
**Key challenge:** Tightly packed rigid form fields; handwritten notes in
CRFs → route to VLM directly.
**Max iterations:** 15

### Sector 8: Consumer Discretionary — Store Audit

**Skill:** `StoreAuditSkill` (NEW)
**Template:** `store_audit_checklist` (NEW)
**Agent Definition:** `def-store-audit`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| store_id | string | header | — |
| audit_date | date | header | — |
| inspector_name | string | header | — |
| cleanliness_score | integer | checklist | 1-5 scale |
| compliance_items[] | list | checklist | each item boolean |
| photo_evidence_count | integer | figures | — |
| violations[] | list | notes | — |
| overall_pass | boolean | derived | all mandatory items pass |

**Tools:** `detect_layout`, `detect_figures`, `ocr`, `vlm`, `crop_image`
**Key challenge:** Blended structured checklists + unstructured photos;
cross-reference visual evidence against textual notes.
**Max iterations:** 15

### Sector 9: Consumer Staples — Thermal Receipt

**Skill:** `ThermalReceiptSkill` (NEW)
**Template:** `thermal_receipt` (NEW)
**Agent Definition:** `def-thermal-receipt`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| merchant_name | string | header | — |
| merchant_address | string | header | — |
| transaction_date | date | header | — |
| transaction_time | time | header | — |
| items[] | table | body | — |
| subtotal | float | footer | sum(items) |
| tax_amount | float | footer | subtotal + tax = total |
| total_amount | float | footer | subtotal + tax = total |
| payment_method | string | footer | — |
| receipt_number | string | footer | — |

**Tools:** `auto_orient`, `deskew`, `denoise`, `threshold`, `ocr`, `vlm`, `crop_image`, `cross_check`
**Key challenge:** Crumpled, faded, skewed, poor lighting. Geometry first,
then perception. Financial invariant: subtotal + tax = total.
**Max iterations:** 12

### Sector 10: Communication Services — Advertising Insertion Order

**Skill:** `AdBuySkill` (NEW)
**Template:** `ad_insertion_order` (NEW)
**Agent Definition:** `def-ad-buy`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| advertiser | string | header | — |
| agency | string | header | — |
| campaign_name | string | header | — |
| campaign_start | date | header | — |
| campaign_end | date | header | start < end |
| total_budget | float | header | sum(local_markets) = total |
| local_markets[] | table | body | each has market, spend, impressions |
| total_impressions | integer | derived | sum(local_markets.impressions) |
| rate_type | string | header | CPM/CPC/CPA |

**Tools:** `detect_layout`, `detect_tables`, `ocr`, `read_table`, `cross_check`
**Key challenge:** Highly stylized tabular documents; local market tiers
must sum to national total.
**Max iterations:** 15

### Sector 11: Utilities — Utility Bill with Chart Extraction

**Skill:** `UtilityBillSkill` (exists — review & harden)
**Template:** `utility_bill` (exists — review & harden)
**Agent Definition:** `def-utility-bill`

| Field | Type | Source | Invariant |
|-------|------|--------|-----------|
| account_number | string | header | — |
| service_address | string | header | — |
| billing_period_start | date | header | — |
| billing_period_end | date | header | start < end |
| current_usage_kwh | float | body | — |
| current_amount | float | body | — |
| trailing_12_month_usage[] | list | chart | 12 data points from chart |
| usage_trend | string | derived | increasing/decreasing/stable |
| due_date | date | footer | — |

**Tools:** `detect_layout`, `ocr`, `read_chart`, `vlm`, `crop_image`
**Key challenge:** Historical usage data only available as bar/line
charts. Bypass OCR, use read_chart tool for visual extraction.
**Max iterations:** 15

## Implementation Plan

### Phase 1: Harden existing (4 items)

1. Review and harden `trade_finance` skill + template
2. Review and harden `bill_of_quantities` skill + template
3. Review and harden `utility_bill` skill + template
4. Review and harden `invoice` skill + template (general purpose)

### Phase 2: New skills (7 items)

5. Implement `ComplianceAuditSkill` + `compliance_audit_soc2` template
6. Implement `CommercialLeaseSkill` + `commercial_lease` template
7. Implement `CommodityTradeSkill` + `commodity_trade_assay` template
8. Implement `MetallurgicalAssaySkill` + `metallurgical_assay` template
9. Implement `MedicalClaimSkill` + `medical_claim_cms1500` template
10. Implement `StoreAuditSkill` + `store_audit_checklist` template
11. Implement `ThermalReceiptSkill` + `thermal_receipt` template
12. Implement `AdBuySkill` + `ad_insertion_order` template

### Phase 3: Prebuilt agent definitions (11 items)

13. Create `def-trade-finance-scrutiny` agent definition
14. Create `def-boq-estimator` agent definition
15. Create `def-compliance-audit` agent definition
16. Create `def-commercial-lease` agent definition
17. Create `def-commodity-trade` agent definition
18. Create `def-metallurgical-assay` agent definition
19. Create `def-medical-claim` agent definition
20. Create `def-store-audit` agent definition
21. Create `def-thermal-receipt` agent definition
22. Create `def-ad-buy` agent definition
23. Create `def-utility-bill` agent definition

### Phase 4: Tests + registration

24. Unit tests for each skill (mocked providers)
25. Register all prebuilt definitions in the Definition Store
26. API endpoints return prebuilt catalogue on `GET /definitions`,
    `GET /skills`, `GET /templates`

## Acceptance Criteria

- [ ] All 11 sector skills implemented with correct tool preferences
- [ ] All 11 sector templates implemented with correct field schemas
- [ ] All 11 prebuilt agent definitions created and registered
- [ ] Each skill has mathematical invariants enforced via `cross_check`
- [ ] Each template has confidence thresholds per field
- [ ] `GET /skills` returns all 12 skills (11 sector + vlm_fallback)
- [ ] `GET /templates` returns all 11 sector templates + invoice
- [ ] `GET /definitions` returns all 11 prebuilt definitions
- [ ] Unit tests for each skill (≥ 2 fixture scenarios)
- [ ] No LLM used for arithmetic — all invariants in deterministic code

## Dependencies

- BLK-016 (AgentDefinition model)
- BLK-017 (Definition Store)
- BLK-042 (Industry skill library — this supersedes and expands BLK-042)

## Constraints

- Each skill must follow the existing `base.py` Skill pattern
- Each template must follow the existing `base.py` Template pattern
- Agent definitions must be serializable and stored in `.adep/definitions/`
- Skills must specify probe order (geometry-first vs perception-first)
- Templates must include per-field confidence thresholds
- All mathematical invariants must be in deterministic code, never LLM
