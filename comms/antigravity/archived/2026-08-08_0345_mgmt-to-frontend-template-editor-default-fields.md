---
from: mgmt
to: frontend
subject: "BLK-107: Template Editor starts with 3 hardcoded invoice fields — should be empty"
date: 2026-08-08T03:45:00+05:30
priority: medium
status: closed
message-id: 2026-08-08_0345_mgmt-to-frontend-template-editor-default-fields
---

## Bug

When creating a new template, the Template Editor pre-fills 3
hardcoded invoice fields: `vendor_name`, `invoice_number`,
`total_amount`. These are leftover demo data.

**Location:** `components/templates/TemplateEditor.tsx` lines 15-20.

The fallback array in `useState` should be `[]`, not 3 invoice fields.

## Fix

1. Change fallback to empty array: `initialTemplate?.fields || []`
2. Add empty state with "Add First Field" button and guidance text
   when `fields.length === 0`

Full spec: `backlog/features/BLK-107_template-editor-hardcoded-default-fields.md`

## Priority

Fix alongside BLK-102 (explanatory text). Both are in the Template
Editor.


## Resolution

Processed and implemented BLK-107 Template Editor Hardcoded Default Fields Fix. Updated components/templates/TemplateEditor.tsx fallback state from 3 hardcoded invoice fields to []. Added empty state card with guidance text and an Add First Field CTA button.
