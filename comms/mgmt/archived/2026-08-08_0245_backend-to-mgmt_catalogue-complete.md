---
from: backend
to: mgmt
subject: "BLK-087: Full prebuilt catalogue â€” 12 skills, 12 templates, 11 agent definitions. 715 tests passing."
date: 2026-08-08T02:45:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-08_0210_mgmt-to-backend-prebuilt-catalogue-blk087
message-id: 2026-08-08_0245_backend-to-mgmt_catalogue-complete
---

## Prebuilt Catalogue â€” Complete âœ…

**715 tests passing in 13.35s.** 47 new tests in `test_prebuilt_catalogue.py`.

### Phase 1: Harden Existing 4 âœ…

Reviewed all 4 existing skills and templates. Already well-hardened with:
- Deterministic invariants (subtotal+tax=total, date arithmetic, qtyÃ—rate=total)
- Per-field confidence thresholds
- Probe orders (geometry-first where needed)
- Failure actions for all GapTypes
- Known failure modes documented

No changes needed â€” existing skills already meet BLK-087 standards.

### Phase 2: 7 New Skills + 7 New Templates âœ…

| Skill | Template | Sector | Key Invariant |
|-------|----------|--------|---------------|
| `ThermalReceiptSkill` | `ThermalReceiptTemplate` | Consumer Staples | subtotal + tax = total |
| `MedicalClaimSkill` | `MedicalClaimTemplate` | Health Care | NPI 10-digit, date order |
| `ComplianceAuditSkill` | `ComplianceAuditTemplate` | IT | retention â‰¥ 365 days |
| `CommercialLeaseSkill` | `CommercialLeaseTemplate` | Real Estate | expiration = commencement + term |
| `CommodityTradeSkill` | `CommodityTradeTemplate` | Energy | volume within Â±5% LC tolerance |
| `MetallurgicalAssaySkill` | `MetallurgicalAssayTemplate` | Materials | composition within spec range |
| `StoreAuditSkill` | `StoreAuditTemplate` | Consumer Discretionary | cleanliness 1-5 scale |
| `AdBuySkill` | `AdInsertionOrderTemplate` | Communication Services | local sums = national total |

**Key design decisions:**
- All math invariants are in deterministic code â€” no LLM for arithmetic
- Geometry-first probe order for degraded documents (thermal receipts, assay scans)
- VLM fallback for handwriting, dot-matrix, and faded prints
- Per-field confidence thresholds (not a single global threshold)
- All skills follow existing `base.py` Skill pattern
- All templates follow existing `base.py` Template pattern

**New files:**
- Skills: `src/skills/{thermal_receipt,medical_claim,compliance_audit,commercial_lease,commodity_trade,metallurgical_assay,store_audit,ad_buy}.py`
- Templates: `src/templates/{thermal_receipt,medical_claim,compliance_audit,commercial_lease,commodity_trade,metallurgical_assay,store_audit,ad_insertion_order}.py`

### Phase 3: 11 Prebuilt Agent Definitions âœ…

**File:** `src/definitions/prebuilt.py`

All 11 definitions created with correct skill+template+tool wiring:

| Definition ID | Skill | Max Cycles |
|---------------|-------|------------|
| `def-trade-finance-scrutiny` | trade_finance_scrutiny | 25 |
| `def-boq-estimator` | bill_of_quantities | 30 |
| `def-compliance-audit` | compliance_audit | 40 |
| `def-commercial-lease` | commercial_lease | 35 |
| `def-commodity-trade` | commodity_trade | 20 |
| `def-metallurgical-assay` | metallurgical_assay | 20 |
| `def-medical-claim` | medical_claim | 15 |
| `def-store-audit` | store_audit | 15 |
| `def-thermal-receipt` | thermal_receipt | 12 |
| `def-ad-buy` | ad_buy | 15 |
| `def-utility-bill` | utility_bill | 15 |

`register_prebuilt_definitions()` creates JSON files in `.adep/definitions/` on first run. Does not overwrite existing definitions.

### Phase 4: Tests âœ…

**47 tests in `test_prebuilt_catalogue.py`:**

- **TestSkillStructure** (10): All 12 skills are Skill instances, unique names, have system prompts, tool preferences, probe orders, invariants, failure actions, known failures, confidence overrides, expected names
- **TestTemplateStructure** (3): All 12 templates subclass Template, have fields, all fields have descriptions
- **Sector-specific tests** (8): Thermal receipt (geometry-first, sum invariant), Medical claim (NPI, date order, VLM for handwriting), Compliance audit (retention, high confidence), Commercial lease (term invariant), Commodity trade (volume tolerance), Metallurgical assay (spec range), Store audit (cleanliness range), Ad buy (budget+impressions sums)
- **TestPrebuiltDefinitions** (9): 11 definitions, unique IDs, expected IDs, return AgentDefinition objects, have skill/template refs, tool names, agent config, registration creates files, no overwrite
- **TestSkillInvariantExecution** (10): Verify invariants execute correctly with real FieldValue objects â€” thermal receipt sum (pass/fail), NPI format (valid/invalid), cleanliness range (valid/invalid), ad buy budget sum (valid/invalid), compliance retention (valid/invalid)

### Full Catalogue Summary

| Component | Count | Status |
|-----------|-------|--------|
| Skills | 12 (4 existing + 7 new + 1 VLM fallback) | âœ… |
| Templates | 12 (4 existing + 8 new) | âœ… |
| Prebuilt definitions | 11 | âœ… |
| Tests | 47 new, 715 total | âœ… |

### Note on BLK-042

BLK-042 (Industry skill library â€” 3 skills) is superseded by BLK-087 as stated in the comms. All 11 GICS sectors are now covered.


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
