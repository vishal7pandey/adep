---
id: BLK-108
type: bug
title: "Prebuilt templates seeded with empty fields — actual field schemas not serialized"
priority: high
status: backlog
phase: 3
owner: backend
created: 2026-08-08T03:50:00+05:30
estimate: M
depends-on: [BLK-092]
tags: [backend, bug, templates, prebuilt, data-integrity, stabilization]
---

## Problem

`seed_store()` in `src/definitions/prebuilt.py` writes all 12
prebuilt templates with `"fields": []`. The actual field schemas
defined in `src/templates/invoice.py`, `src/templates/utility_bill.py`,
etc. are never serialized into the store JSON files.

This means:
- `GET /api/v1/templates` returns templates with zero fields
- Frontend list page shows "0 fields" for every template
- Template Editor shows no existing fields when editing
- Users cannot view or edit the actual extraction schema

## Root Cause

`PREBUILT_TEMPLATES` at line 233:

```python
PREBUILT_TEMPLATES: list[dict] = [
    {"id": "invoice", "name": "Invoice", "description": "Standard invoice template", "fields": []},
    {"id": "trade_finance_mt700", "name": "Trade Finance MT700", "description": "MT700 letter of credit template", "fields": []},
    # ... all 12 have "fields": []
]
```

The Python Template classes (e.g., `InvoiceTemplate` in
`src/templates/invoice.py`) define the actual fields as Pydantic
schema, but `seed_store()` doesn't extract or serialize them.

## Fix

Two options:

### Option A (preferred): Serialize from Template classes

Import each Template class, extract its field schemas, and include
them in `PREBUILT_TEMPLATES`:

```python
from src.templates.invoice import InvoiceTemplate
from src.templates.utility_bill import UtilityBillTemplate
# ... etc.

def _extract_fields(template_cls) -> list[dict]:
    """Extract field schemas from a Template Pydantic model."""
    fields = []
    for name, field_info in template_cls.model_fields.items():
        fields.append({
            "name": name,
            "type": _pydantic_type_to_str(field_info.annotation),
            "description": field_info.description or "",
            "required": field_info.is_required(),
            "confidence_threshold": 0.7,  # default, override per field
        })
    return fields

PREBUILT_TEMPLATES = [
    {"id": "invoice", "name": "Invoice", "description": "Standard invoice template",
     "fields": _extract_fields(InvoiceTemplate)},
    # ... etc.
]
```

### Option B: Manually define fields in PREBUILT_TEMPLATES

Explicitly list all fields for each template in the dict. More
verbose but simpler.

## Acceptance Criteria

- [ ] All 12 seeded templates have non-empty `fields` arrays
- [ ] Fields match the Pydantic schema defined in the Template class
- [ ] `GET /api/v1/templates` returns templates with fields populated
- [ ] Frontend list page shows correct field counts
- [ ] Template Editor shows existing fields when clicking Edit
- [ ] No regression in existing tests
- [ ] Re-seeding works (doesn't overwrite existing templates)

## Notes

- This is the root cause of the "Edit button doesn't show existing
  template" issue reported by the user
- Frontend mock data has 6 fields for the invoice template — the
  real backend should match or exceed that
- The `confidence_threshold` per field should come from the Template
  class if defined, or default to 0.7
