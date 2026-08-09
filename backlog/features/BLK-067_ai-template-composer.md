---
id: BLK-067
type: feature
title: "AI Template Composer — generate extraction schemas from natural language"
priority: high
status: assigned
phase: 5
owner: backend
created: 2026-08-08T00:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-030]
tags: [ai, adas, template-composer, natural-language, schema-generation, research]
---

## Description

A meta-agent that converts a natural language description of desired
extraction output into a Pydantic-based Template schema. The user types
something like:

> "Extract vendor name, invoice number, invoice date, line items with
> quantity, rate, and total, plus the final total including tax."

The AI Template Composer produces a complete Template with field names,
types, required flags, confidence thresholds, and descriptions.

## Motivation

From `agentic agent builder.md`: manual template configuration is
inefficient. The Template Composer is the first primitive in the
ADAS (Automated Design of Agentic Systems) vision, turning user intent
into a structured outcome contract automatically.

## Design

**Input:**
- Natural language description
- Optional: 1-3 sample documents for context
- Optional: target confidence threshold

**Output:**
```json
{
  "name": "Generated Invoice Schema",
  "fields": [
    {"name": "vendor_name", "type": "string", "required": true, "threshold": 0.8},
    {"name": "invoice_number", "type": "string", "required": true, "threshold": 0.85},
    {"name": "line_items", "type": "list", "required": true, "sub_fields": [...]}
  ]
}
```

**Implementation:**
- LLM call with system prompt: "Generate a Pydantic schema..."
- Structured output via PydanticAI or Instructor
- Validation: ensure field names are snake_case, types supported,
  grounding possible
- User can edit generated schema before saving

**UI:**
- "Auto-generate from description" button in Template Editor
- Textarea for description
- "Generate" button → loading spinner → editable schema
- User reviews, edits, saves

## Acceptance Criteria

- [ ] `POST /api/v1/templates/generate` accepts description and returns
      generated template
- [ ] Frontend "Auto-generate" button in Template Editor
- [ ] Generated template editable before save
- [ ] Handles simple and nested schemas
- [ ] Confidence threshold defaults based on field type
- [ ] Field names normalized to snake_case
- [ ] Validation: reject unsupported types
- [ ] Test: NL description → schema with 5+ fields generated correctly

## Constraints

- v1: no vision model understanding of sample docs (deferred)
- Generated schema must be reviewed — not auto-saved
- Use existing Template Editor for manual refinement

## Dependencies

- BLK-030 (Template Editor)

## Notes

- `agentic agent builder.md`: Template Composer = first primitive
- Uses PydanticAI or Instructor for schema-first generation
