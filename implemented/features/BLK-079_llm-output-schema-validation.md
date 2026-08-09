---
id: BLK-079
type: feature
title: "LLM output schema validation & sanitization"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T01:45:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-043]
tags: [backend, security, guardrails, validation, sanitization, llm]
---

## Description

Every LLM response must be validated against an expected schema before
it is used. The LLM is a perception engine — its output is untrusted
input to the rest of the system. No LLM output reaches tool execution,
state mutation, or user display without passing through a Pydantic
validator.

## Motivation

LLMs hallucinate. They return malformed JSON, extra fields, wrong types,
and sometimes inject instructions into their output. Without a strict
validation layer, a malformed LLM response could crash the agent or,
worse, cause it to execute unintended actions.

## Guardrails

1. **Schema validation:** Every LLM call has a corresponding Pydantic
   model. If `response.parse()` fails, the agent retries (up to 2x)
   with a corrective prompt, then marks the field as failed.

2. **Field allowlist:** Unknown fields in LLM output are silently
   dropped, not passed through. Log a warning.

3. **Type coercion safety:** Strings that should be numbers/dates are
   coerced with strict parsing. If coercion fails, the value is `null`
   with `confidence: 0.0`.

4. **Output length limits:** LLM responses are truncated to a max token
   count (configurable, default 4096). Prevents runaway generation.

5. **Instruction pattern sanitization:** Scan LLM output for instruction-
   like patterns (same patterns as BLK-043 input defense). If detected,
   log a warning and strip the pattern from the output.

6. **No raw LLM output in tool args:** Tool arguments are constructed
   from validated fields, not from raw LLM text. The LLM never directly
   specifies tool arguments as free-form strings.

## Acceptance Criteria

- [ ] Every `llm_client.invoke()` call has a Pydantic response model
- [ ] Invalid responses trigger retry with corrective prompt
- [ ] Unknown fields in LLM output are dropped + logged
- [ ] Output is truncated at configurable max token limit
- [ ] Instruction patterns in output are detected and stripped
- [ ] Tool arguments are always constructed from validated fields
- [ ] Unit tests: malformed JSON, extra fields, wrong types, oversized output

## Dependencies

- BLK-043 (prompt injection defense — shares pattern detection)
