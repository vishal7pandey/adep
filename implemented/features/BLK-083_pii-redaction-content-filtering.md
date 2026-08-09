---
id: BLK-083
type: feature
title: "PII redaction & content filtering"
priority: medium
status: backlog
phase: 4
owner: backend
created: 2026-08-08T01:45:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-079]
tags: [backend, security, guardrails, pii, privacy, content-filtering, compliance]
---

## Description

Scan LLM inputs and outputs for personally identifiable information
(PII) and sensitive content. Redact PII before it enters the LLM prompt,
and filter sensitive content from LLM responses before display.

## Motivation

Documents (invoices, contracts, medical records) contain PII: names,
addresses, SSNs, account numbers. Sending raw PII to an external LLM API
is a privacy risk. Displaying raw PII in the UI without redaction may
violate compliance requirements (GDPR, HIPAA).

## Guardrails

1. **PII detection in document text:** Before OCR text is included in
   the LLM prompt, scan for PII patterns:
   - SSN: `\d{3}-\d{2}-\d{4}`
   - Credit card: Luhn-validated 13-19 digit numbers
   - Email: standard regex
   - Phone: international formats
   - IBAN: `\w{2}\d{2}[A-Z0-9]{10,30}`
   
   Replace with `[REDACTED:SSN]`, `[REDACTED:CC]`, etc.

2. **PII preservation in extraction:** The extracted value is preserved
   (the user needs it), but the trace/log redacts PII. The LLM prompt
   contains redacted text; the extraction result contains the real value.

3. **Content classification:** Tag each document with a sensitivity
   level: `public`, `internal`, `confidential`, `restricted`. Restrict
   which LLM providers can be used based on sensitivity (e.g.,
   `restricted` documents use only on-prem models).

4. **Audit log redaction:** Trace logs and token usage logs redact PII.
   Only the extraction result (viewed by the user in the UI) contains
   raw values.

5. **Configurable redaction:** Admin can toggle which PII types are
   redacted, add custom patterns, and set sensitivity thresholds.

## Acceptance Criteria

- [ ] PII patterns detected and redacted in LLM prompts
- [ ] Extraction results preserve real values
- [ ] Trace logs redact PII
- [ ] Document sensitivity level classified
- [ ] LLM provider restricted by sensitivity level
- [ ] Custom PII patterns configurable via settings
- [ ] Unit tests: SSN, CC, email, phone, IBAN redaction

## Dependencies

- BLK-079 (output schema validation)
