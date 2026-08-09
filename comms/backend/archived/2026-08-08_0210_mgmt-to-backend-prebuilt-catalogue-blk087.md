---
from: mgmt
to: backend
subject: "BLK-087: Implement full prebuilt catalogue — 11 GICS sector agents, skills, and templates"
date: 2026-08-08T02:10:00+05:30
priority: high
status: new
message-id: 2026-08-08_0210_mgmt-to-backend-prebuilt-catalogue-blk087
---

## Context

The ADE Industry Mapping document identifies 11 GICS sectors with
distinct document extraction use cases. Currently we have 4 skills
(invoice, trade_finance, bill_of_quantities, utility_bill) and 4
templates, but **zero prebuilt agent definitions**. We need a full,
solid catalogue so users can immediately select an agent for their
document type without building one from scratch.

## What Exists

**Skills (in `src/skills/`):**
- `invoice.py` — general invoice extraction
- `trade_finance.py` — MT700 / LC scrutiny
- `bill_of_quantities.py` — construction BOQ
- `utility_bill.py` — utility bill with chart extraction
- `vlm_fallback.py` — generic VLM fallback skill

**Templates (in `src/templates/`):**
- `invoice.py`, `trade_finance.py`, `bill_of_quantities.py`,
  `utility_bill.py`

**Prebuilt agent definitions:** None. The Definition Store
(`src/definitions/store.py`) exists but has no prebuilt definitions
shipped with the platform.

## What's Needed

### 7 New Skills

| Skill | Sector | Key Challenge |
|-------|--------|---------------|
| `ComplianceAuditSkill` | IT | 100+ page SOC 2 / OSPAR docs |
| `CommercialLeaseSkill` | Real Estate | 60+ page leases, context dilution |
| `CommodityTradeSkill` | Energy | Volumetric reconciliation across docs |
| `MetallurgicalAssaySkill` | Materials | Degraded scans, dot-matrix, OCR fallback |
| `MedicalClaimSkill` | Health Care | Rigid CMS-1500 forms, handwritten CRFs |
| `StoreAuditSkill` | Consumer Discretionary | Blended checklists + photo evidence |
| `ThermalReceiptSkill` | Consumer Staples | Crumpled/faded thermal paper, geometry-first |
| `AdBuySkill` | Communication Services | Stylized tables, local sums = national |

### 7 New Templates

Each template defines the field schema with types, confidence
thresholds, and invariants. See the full spec for field lists.

### 11 Prebuilt Agent Definitions

Each definition wires a skill + template + tool set + system prompt +
max iterations. These are shipped as JSON files in
`.adep/definitions/` so they appear immediately in the UI.

### Harden Existing 4

Review and harden the existing 4 skills/templates:
- Ensure invariants are in deterministic code
- Ensure confidence thresholds are set per field
- Ensure probe order is specified (geometry-first vs perception-first)

## Full Spec

`backlog/features/BLK-087_prebuilt-catalogue-gics-sectors.md`

This contains the complete field schema, invariants, tool preferences,
and max iterations for every sector. **Read it carefully** — it's the
authoritative source.

## Implementation Order

1. **Harden existing 4** (trade_finance, boq, utility_bill, invoice)
2. **Implement 7 new skills** (one per sector, following `base.py` pattern)
3. **Implement 7 new templates** (one per sector, following `base.py` pattern)
4. **Create 11 prebuilt agent definitions** (JSON files in `.adep/definitions/`)
5. **Register in Definition Store** — `GET /definitions`, `GET /skills`,
   `GET /templates` must return the full catalogue
6. **Unit tests** — at least 2 fixture scenarios per skill

## Key Principles

- **No LLM for arithmetic** — all mathematical invariants (sums, date
  comparisons, tolerance checks) must be in deterministic code via
  `cross_check` tool
- **Probe order matters** — degraded documents (thermal receipts, assay
  scans) should do geometry first (deskew, denoise) then perception
- **Confidence thresholds per field** — not a single global threshold
- **Follow existing patterns** — `src/skills/base.py` and
  `src/templates/base.py` define the interface

## Priority

This is a large item (estimate: L). Start with hardening existing
skills, then implement new ones in this order:
1. `ThermalReceiptSkill` (small, self-contained, demonstrates geometry-first)
2. `MedicalClaimSkill` (demonstrates form-based extraction)
3. `ComplianceAuditSkill` (demonstrates long document navigation)
4. `CommercialLeaseSkill` (demonstrates multi-page hierarchical state)
5. `CommodityTradeSkill` (demonstrates cross-document reconciliation)
6. `MetallurgicalAssaySkill` (demonstrates OCR fallback to VLM)
7. `StoreAuditSkill` (demonstrates figure/visual evidence handling)
8. `AdBuySkill` (demonstrates tabular sum invariants)

## Supersedes BLK-042

BLK-042 (Industry skill library — 3 skills) is superseded by BLK-087.
BLK-087 covers all 11 sectors with full schemas.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
