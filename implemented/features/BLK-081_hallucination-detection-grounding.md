---
id: BLK-081
type: feature
title: "Hallucination detection & grounding enforcement"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T01:45:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-079, BLK-080]
tags: [backend, security, guardrails, hallucination, grounding, confidence]
---

## Description

Detect and reject hallucinated extractions. Every extracted field must
have a grounding bbox that points to actual document content. Fields
without grounding, or with grounding that doesn't match the OCR/text
layer, are flagged as hallucinations.

## Motivation

LLMs can fabricate values that look plausible but don't appear in the
document. Without grounding enforcement, the user gets confident-looking
output that is entirely made up. This is the most dangerous failure mode
for a document extraction platform.

## Guardrails

1. **Mandatory grounding:** Every extracted field must include a `bbox`
   and `page`. Fields without grounding are rejected with
   `status: 'ungrounded'` and `confidence: 0.0`.

2. **Grounding verification:** The bbox region is cross-checked against
   the OCR text layer. If the extracted value does not appear (fuzzy
   match, Levenshtein ≤ 2) within the bbox region, the field is flagged
   as `status: 'hallucination_suspected'`.

3. **Confidence calibration:** Fields with grounding mismatch get
   `confidence` capped at 0.3, regardless of what the LLM claimed.

4. **Cross-field consistency checks:** Simple invariants (e.g., 
   `total_amount = subtotal + tax_amount`) are validated. Violations
   flag the fields as `status: 'invariant_violation'`.

5. **Source text preservation:** The raw OCR text at the bbox location
   is stored alongside the extracted value. The UI can show "LLM said: X,
   document says: Y" for verification.

6. **Hallucination rate metric:** Track per-run, per-definition, and
   per-skill hallucination rates. Alert if rate exceeds threshold (default 15%).

## Acceptance Criteria

- [ ] Fields without bbox are rejected with `status: 'ungrounded'`
- [ ] Grounding mismatch detected via fuzzy text match
- [ ] Mismatched fields get `confidence` capped at 0.3
- [ ] Cross-field invariants validated
- [ ] Raw source text stored per field
- [ ] Hallucination rate tracked and alertable
- [ ] Unit tests: fabricated value, wrong bbox, invariant violation

## Dependencies

- BLK-079 (output schema validation)
- BLK-080 (tool call guardrails — for bbox validation)
