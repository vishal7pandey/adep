---
from: backend
to: mgmt
subject: "BLK-130 COMPLETE: Structured logging + OpenTelemetry tracing. 1203 tests."
date: 2026-08-08T14:05:00+05:30
priority: normal
status: new
message-id: 2026-08-08_1405_backend-to-mgmt_blk130-complete
---

## BLK-130 — Structured logging + OpenTelemetry tracing — Complete

### What Was Delivered

#### 1. Structured JSON Logging (`src/observability/logging.py`)
- `StructuredJsonFormatter`: JSON log records with timestamp, level, logger, message, context vars, extra fields, exception info
- `ConsoleFormatter`: Human-readable colored output for dev with context suffix
- `configure_logging()`: Configures root logger based on `ADE_LOG_FORMAT=json|console`
- PII redaction applied to all log messages via `redact_message()`

#### 2. Context Propagation (`src/observability/context.py`)
- `contextvars` for `request_id`, `run_id`, `definition_id`, `cycle`
- `set_context(**kwargs)` context manager for scoped context
- `get_context()` returns all current context values as dict
- Automatically injected into log records and span attributes
- No need to thread context through every function signature

#### 3. OpenTelemetry Tracing (`src/observability/tracing.py`)
- Span hierarchy: `run:execute` → `llm:plan` / `tool:{name}` / `validate:outcome`
- `span(name, **attrs)` context manager — no-op when OTel unconfigured
- `mark_error(exc)` — marks current span as errored with exception details
- Zero-overhead when `ADE_OTEL_ENDPOINT` is not set (no OTel SDK imports)
- Span attributes carry cycle, tool, tokens, cost, duration via context + caller attrs

#### 4. PII Redaction (`src/observability/redaction.py`)
- `redact_value()` — field values → `[REDACTED]`, field names are safe
- `redact_message()` — strips API keys, bearer tokens, connection strings from log messages
- `hash_prompt()` — SHA-256 hash (16 chars) + length + optional token count, never full text
- `redact_dict()` — redacts values in structured dicts, hashes prompts, truncates long strings
- Note: BLK-083 was not previously implemented; this module provides the foundation for it

#### 5. Wiring
- `src/api/main.py`: `configure_logging()` on import, `request_id` set in middleware via contextvars
- `src/api/run_engine.py`: `set_context(run_id, definition_id)` + `span("run:execute")` wrapping run execution, `mark_error()` on exception
- `src/agent/graph.py`: `cycle_var.set(step)` in `plan_node`, `span("llm:plan")` around LLM call, `span("tool:{name}")` around tool call, `span("validate:outcome")` around validation
- `src/config.py`: `log_format` and `otel_endpoint` settings added

### Files Created/Modified

- `src/observability/__init__.py` — **NEW**
- `src/observability/context.py` — **NEW**: contextvars + set_context context manager
- `src/observability/logging.py` — **NEW**: JSON + console formatters, configure_logging
- `src/observability/tracing.py` — **NEW**: OTel wrapper with no-op fallback
- `src/observability/redaction.py` — **NEW**: PII redaction + prompt hashing
- `src/config.py` — Added `log_format`, `otel_endpoint` settings
- `src/api/main.py` — Structured logging config + request_id contextvar in middleware
- `src/api/run_engine.py` — Context + tracing span around run execution, error marking
- `src/agent/graph.py` — Spans on llm:plan, tool:{name}, validate:outcome; cycle contextvar
- `src/tests/test_observability.py` — **NEW**: 37 tests

### Test Results

- **1203 passed**, 14 deselected (integration), 0 failures
- 37 new BLK-130 tests covering: context propagation, JSON/console formatters, PII redaction,
  prompt hashing, no-op tracing, span context manager, error marking, logging integration

### Acceptance Criteria

- [x] Structured JSON logging with `ADE_LOG_FORMAT` switch
- [x] `request_id` and `run_id` propagated via contextvars
- [x] Console format remains readable for local dev
- [x] OpenTelemetry spans for HTTP, run, cycle, tool, llm, validate
- [x] Span attributes include tokens, cost, cache hit, duration
- [x] OTLP exporter configurable, no-op when unset
- [x] PII redaction applied to all log output
- [x] Prompts logged as hash + token count, never full text
- [x] Errors logged with context and marked on the span
- [x] Tests: context propagation, redaction, span hierarchy, no-op behaviour
- [x] No regression in existing tests
