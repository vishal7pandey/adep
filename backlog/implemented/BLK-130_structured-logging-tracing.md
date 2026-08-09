---
id: BLK-130
type: feature
title: "Structured logging + OpenTelemetry tracing"
priority: medium
status: backlog
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: []
tags: [backend, observability, logging, tracing, opentelemetry]
---

## Problem

Logging is unstructured `logger.info("%s %s %d %.1fms ...")` string
formatting. There is no correlation between an HTTP request, the run
it started, the ReAct cycles inside it, and the provider calls those
cycles made.

When a run behaves badly in production, there is no way to answer
"where did the time go?" or "which provider call failed?" without
reading raw log text.

## Requirements

### 1. Structured JSON Logging

Replace string-formatted logs with structured records:

```json
{
  "timestamp": "2026-08-08T13:50:00.123Z",
  "level": "INFO",
  "logger": "src.agent.graph",
  "message": "tool call completed",
  "request_id": "a1b2c3d4",
  "run_id": "run-0042",
  "definition_id": "def-invoice",
  "cycle": 3,
  "field": "invoice_number",
  "tool": "ocr",
  "duration_ms": 412,
  "tokens_in": 0,
  "tokens_out": 0,
  "cache_hit": true
}
```

- Human-readable console format in dev, JSON in production
  (`ADE_LOG_FORMAT=json|console`)
- Context propagated via `contextvars` so `run_id` and `request_id`
  are attached automatically without threading them through every
  function signature

### 2. OpenTelemetry Tracing

Span hierarchy:

```
HTTP POST /api/v1/runs
  run:execute (run_id, definition_id)
    react:cycle (cycle=1)
      tool:ocr (provider=paddle, cache_hit=false, duration_ms=412)
      llm:plan (tokens_in=1200, tokens_out=80, cost_usd=0.007)
    react:cycle (cycle=2)
      tool:vlm (provider=azure, tokens_in=900, tokens_out=120)
    validate:outcome (gaps=2)
```

- OTLP exporter, endpoint via `ADE_OTEL_ENDPOINT`
- Disabled by default; no-op when unconfigured so tests and local dev
  are unaffected
- Span attributes carry tokens, cost, cache hit/miss, confidence

### 3. Redaction

Logs and spans must never contain:
- API keys or credentials
- Raw document content or extracted PII field values
- Full prompt text (log a hash and token count instead)

Reuse the existing PII redaction from BLK-083 rather than writing a
second implementation. Field **names** are fine to log; field
**values** are not.

### 4. Error Context

On exception, log the structured context plus a stack trace, and mark
the span as errored with the exception type. No bare
`except: pass` anywhere in the run path.

## Acceptance Criteria

- [ ] Structured JSON logging with `ADE_LOG_FORMAT` switch
- [ ] `request_id` and `run_id` propagated via contextvars
- [ ] Console format remains readable for local dev
- [ ] OpenTelemetry spans for HTTP, run, cycle, tool, llm, validate
- [ ] Span attributes include tokens, cost, cache hit, duration
- [ ] OTLP exporter configurable, no-op when unset
- [ ] PII redaction applied to all log output, reusing BLK-083
- [ ] Prompts logged as hash + token count, never full text
- [ ] Errors logged with context and marked on the span
- [ ] Tests: context propagation, redaction, span hierarchy,
      no-op behaviour when OTEL is unconfigured
- [ ] No regression in existing tests

## Constraints

- Must be zero-overhead when tracing is disabled
- Do not add a heavyweight logging framework; stdlib `logging` with a
  JSON formatter is sufficient
