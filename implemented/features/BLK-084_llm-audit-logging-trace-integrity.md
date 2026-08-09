---
id: BLK-084
type: feature
title: "LLM call audit logging & trace integrity"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T01:45:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-050, BLK-079, BLK-080]
tags: [backend, security, guardrails, audit, logging, trace, observability, compliance]
---

## Description

Every LLM call is logged with full context: input prompt, output
response, token usage, tool calls triggered, validation results, and
guardrail decisions. Logs are tamper-evident and retained per policy.

## Motivation

When an extraction produces a wrong result, we need to trace exactly
what happened: what the LLM was asked, what it returned, whether
guardrails fired, and where the error occurred. Without comprehensive
audit logging, debugging is guesswork and compliance is impossible.

## Guardrails

1. **LLM call log entry:** Every `llm_client.invoke()` call records:
   - Timestamp, run ID, cycle number, node name
   - System prompt hash (not full prompt — too large)
   - User prompt (full, with PII redacted per BLK-083)
   - LLM response (full)
   - Token usage (input, output, total, cost)
   - Latency (ms)
   - Validation result (passed/failed/retried)
   - Guardrail actions taken (sanitization, truncation, rejection)

2. **Tamper-evident logging:** Log entries are chained (each entry
   includes a hash of the previous entry). Tampering breaks the chain.

3. **Log retention policy:** Configurable retention (default 30 days).
   Logs are stored in `.adep/runs/{run_id}/audit_log.jsonl`.

4. **Guardrail decision log:** Separate log for guardrail actions:
   - Which guardrail fired (schema validation, tool sandbox, loop
     detection, hallucination detection, PII redaction)
   - What was rejected/sanitized
   - What corrective action was taken (retry, terminate, flag)

5. **Export:** Audit logs exportable as JSON, CSV (for compliance review).

6. **Real-time streaming:** Audit events stream via SSE for live
   monitoring in the admin panel.

## Acceptance Criteria

- [ ] Every LLM call logged with full context
- [ ] Log entries are chained (tamper-evident)
- [ ] PII redacted in logs
- [ ] Guardrail decisions logged separately
- [ ] Logs persist to `audit_log.jsonl` per run
- [ ] Logs exportable as JSON and CSV
- [ ] Audit events stream via SSE
- [ ] Retention policy enforced (auto-delete after N days)
- [ ] Unit tests: log entry format, chain integrity, export format

## Dependencies

- BLK-050 (token tracking — shares token data)
- BLK-079 (output validation — logs validation results)
- BLK-080 (tool guardrails — logs tool call decisions)
