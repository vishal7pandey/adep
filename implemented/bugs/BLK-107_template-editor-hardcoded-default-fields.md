---
id: BLK-107
type: bug
title: "Template Editor starts with 3 hardcoded invoice fields on new template"
priority: medium
status: backlog
phase: 3
owner: frontend
created: 2026-08-08T03:45:00+05:30
estimate: S
depends-on: []
tags: [frontend, bug, template-editor, demo-data, stabilization]
---

## Problem

When creating a new template, the Template Editor pre-fills 3
hardcoded invoice-specific fields (`vendor_name`, `invoice_number`,
`total_amount`). These are leftover demo data from initial
scaffolding.

A new template should start with **zero fields**. The user should
see an empty state with an "Add First Field" button.

## Location

`frontend/components/templates/TemplateEditor.tsx` lines 15-20:

```tsx
const [fields, setFields] = useState<FieldSchema[]>(
  initialTemplate?.fields || [
    { name: 'vendor_name', type: 'string', description: 'Billing vendor name', required: true, confidence_threshold: 0.8 },
    { name: 'invoice_number', type: 'string', description: 'Unique invoice reference number', required: true, confidence_threshold: 0.85 },
    { name: 'total_amount', type: 'number', description: 'Grand total invoice amount', required: true, confidence_threshold: 0.9 },
  ]
);
```

## Fix

Change the fallback to an empty array:

```tsx
const [fields, setFields] = useState<FieldSchema[]>(
  initialTemplate?.fields || []
);
```

Then add an empty state when `fields.length === 0`:

```tsx
{fields.length === 0 && (
  <div className="text-center py-8 text-muted">
    <p>No fields defined yet.</p>
    <p className="text-xs mt-1">
      Add fields to specify what the agent should extract from this document type.
    </p>
    <AdeButton variant="secondary" size="sm" onClick={addField}>
      <Plus className="w-3.5 h-3.5" /> Add First Field
    </AdeButton>
  </div>
)}
```

## Acceptance Criteria

- [ ] New template starts with zero fields
- [ ] Empty state shows "Add First Field" button with guidance text
- [ ] Editing existing template still loads its fields correctly
- [ ] No regression in save/clone functionality
