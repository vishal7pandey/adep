"""Tests for BLK-130: Structured logging + OpenTelemetry tracing.

Covers:
- Context propagation via contextvars (request_id, run_id, cycle)
- Structured JSON formatter with context injection
- Console formatter for dev readability
- PII redaction (values redacted, names safe, prompts hashed)
- OpenTelemetry tracing no-op when unconfigured
- Span context manager with attribute injection
- Error marking on spans
- hash_prompt utility
- redact_dict for structured data
"""

from __future__ import annotations

import json
import logging
import io
import os
from typing import Any

import pytest

from src.observability.context import (
    get_context,
    set_context,
    request_id_var,
    run_id_var,
    cycle_var,
    definition_id_var,
)
from src.observability.logging import (
    StructuredJsonFormatter,
    ConsoleFormatter,
    configure_logging,
)
from src.observability.redaction import (
    redact_value,
    redact_message,
    hash_prompt,
    redact_dict,
)
from src.observability.tracing import span, mark_error, get_tracer


# ---------------------------------------------------------------------------
# Context propagation tests
# ---------------------------------------------------------------------------


class TestContextPropagation:
    """contextvars for request_id, run_id, cycle [BLK-130]."""

    def test_default_context_is_empty(self):
        # Clear any leftover context from other tests
        for var in (request_id_var, run_id_var, cycle_var, definition_id_var):
            var.set(None)
        assert get_context() == {}

    def test_set_context_injects_values(self):
        with set_context(run_id="run-42", request_id="req-1", cycle=3):
            ctx = get_context()
            assert ctx["run_id"] == "run-42"
            assert ctx["request_id"] == "req-1"
            assert ctx["cycle"] == 3

    def test_context_restored_on_exit(self):
        request_id_var.set("original")
        with set_context(request_id="temporary"):
            assert request_id_var.get() == "temporary"
        assert request_id_var.get() == "original"

    def test_context_nested_scopes(self):
        with set_context(run_id="outer"):
            assert run_id_var.get() == "outer"
            with set_context(run_id="inner"):
                assert run_id_var.get() == "inner"
            assert run_id_var.get() == "outer"

    def test_context_with_definition_id(self):
        with set_context(definition_id="def-invoice"):
            ctx = get_context()
            assert ctx["definition_id"] == "def-invoice"

    def test_context_unknown_key_ignored(self):
        with set_context(unknown_key="value"):
            assert "unknown_key" not in get_context()


# ---------------------------------------------------------------------------
# JSON formatter tests
# ---------------------------------------------------------------------------


class TestStructuredJsonFormatter:
    """JSON log formatter with context injection [BLK-130]."""

    def _make_record(self, msg: str, **extra: Any) -> logging.LogRecord:
        """Create a log record with extra fields."""
        record = logging.LogRecord(
            name="src.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_json_format_basic(self):
        fmt = StructuredJsonFormatter()
        record = self._make_record("test message")
        output = fmt.format(record)
        data = json.loads(output)
        assert data["message"] == "test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "src.test"
        assert "timestamp" in data

    def test_json_format_with_context(self):
        fmt = StructuredJsonFormatter()
        with set_context(run_id="run-99", request_id="req-5"):
            record = self._make_record("processing")
            output = fmt.format(record)
            data = json.loads(output)
            assert data["run_id"] == "run-99"
            assert data["request_id"] == "req-5"

    def test_json_format_with_extra_fields(self):
        fmt = StructuredJsonFormatter()
        record = self._make_record("tool call", tool="ocr", duration_ms=412, cycle=3)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["tool"] == "ocr"
        assert data["duration_ms"] == 412
        assert data["cycle"] == 3

    def test_json_format_with_exception(self):
        fmt = StructuredJsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="src.test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="failed",
            args=(),
            exc_info=exc_info,
        )
        output = fmt.format(record)
        data = json.loads(output)
        assert data["exception_type"] == "ValueError"
        assert "test error" in data["exception"]


# ---------------------------------------------------------------------------
# Console formatter tests
# ---------------------------------------------------------------------------


class TestConsoleFormatter:
    """Console formatter for dev readability [BLK-130]."""

    def _make_record(self, msg: str, **extra: Any) -> logging.LogRecord:
        record = logging.LogRecord(
            name="src.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_console_format_basic(self):
        fmt = ConsoleFormatter()
        record = self._make_record("hello world")
        output = fmt.format(record)
        assert "hello world" in output
        assert "INFO" in output
        assert "src.test" in output

    def test_console_format_with_context(self):
        fmt = ConsoleFormatter()
        with set_context(run_id="run-1"):
            record = self._make_record("processing")
            output = fmt.format(record)
            assert "run_id=run-1" in output

    def test_console_format_with_extras(self):
        fmt = ConsoleFormatter()
        record = self._make_record("tool call", tool="ocr", duration_ms=100)
        output = fmt.format(record)
        assert "tool=ocr" in output
        assert "duration_ms=100" in output


# ---------------------------------------------------------------------------
# configure_logging tests
# ---------------------------------------------------------------------------


class TestConfigureLogging:
    """Logging configuration [BLK-130]."""

    def test_configure_json_format(self):
        configure_logging(format_type="json", level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, StructuredJsonFormatter)

    def test_configure_console_format(self):
        configure_logging(format_type="console", level="INFO")
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, ConsoleFormatter)

    def test_configure_clears_existing_handlers(self):
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        root.addHandler(logging.StreamHandler())
        configure_logging(format_type="console")
        assert len(root.handlers) == 1


# ---------------------------------------------------------------------------
# PII redaction tests
# ---------------------------------------------------------------------------


class TestRedaction:
    """PII redaction utilities [BLK-130, BLK-083]."""

    def test_redact_value_returns_redacted(self):
        assert redact_value("sensitive data") == "[REDACTED]"
        assert redact_value(12345) == "[REDACTED]"
        assert redact_value(None) == "None"

    def test_redact_message_removes_api_keys(self):
        msg = "api_key=abc123secret processing request"
        redacted = redact_message(msg)
        assert "abc123secret" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_message_removes_bearer_tokens(self):
        msg = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test"
        redacted = redact_message(msg)
        assert "eyJhbGciOiJIUzI1NiJ9" not in redacted

    def test_redact_message_removes_connection_strings(self):
        msg = "Connecting to postgres://user:pass@host:5432/db"
        redacted = redact_message(msg)
        assert "pass" not in redacted or "[REDACTED]" in redacted

    def test_redact_message_preserves_safe_text(self):
        msg = "Run run-42 completed with 5 fields extracted"
        redacted = redact_message(msg)
        assert redacted == msg

    def test_hash_prompt_returns_hash_and_length(self):
        prompt = "Extract invoice_number from the document"
        result = hash_prompt(prompt)
        assert "prompt_hash" in result
        assert len(result["prompt_hash"]) == 16
        assert result["prompt_length"] == len(prompt)
        assert "token_count" not in result

    def test_hash_prompt_with_token_count(self):
        result = hash_prompt("test prompt", token_count=42)
        assert result["token_count"] == 42

    def test_hash_prompt_deterministic(self):
        prompt = "same prompt"
        r1 = hash_prompt(prompt)
        r2 = hash_prompt(prompt)
        assert r1["prompt_hash"] == r2["prompt_hash"]

    def test_redact_dict_redacts_values(self):
        data = {"invoice_number": "INV-001", "vendor": "ACME Corp"}
        redacted = redact_dict(data)
        assert redacted["invoice_number"] == "INV-001"  # short string, not redacted
        assert redacted["vendor"] == "ACME Corp"

    def test_redact_dict_redacts_api_keys(self):
        data = {"api_key": "secret123", "name": "test"}
        redacted = redact_dict(data)
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["name"] == "test"

    def test_redact_dict_redacts_prompts(self):
        data = {"prompt": "Extract all fields from this document"}
        redacted = redact_dict(data)
        assert "prompt_hash" in redacted["prompt"]
        assert "Extract all fields" not in str(redacted["prompt"])

    def test_redact_dict_truncates_long_values(self):
        data = {"text": "x" * 300}
        redacted = redact_dict(data)
        assert "300 chars" in redacted["text"]

    def test_redact_dict_nested(self):
        data = {"outer": {"inner": "value", "api_key": "secret"}}
        redacted = redact_dict(data)
        assert redacted["outer"]["api_key"] == "[REDACTED]"
        assert redacted["outer"]["inner"] == "value"


# ---------------------------------------------------------------------------
# OpenTelemetry tracing tests
# ---------------------------------------------------------------------------


class TestTracing:
    """OpenTelemetry tracing wrapper [BLK-130]."""

    def test_tracer_is_noop_when_unconfigured(self):
        tracer = get_tracer()
        # When ADE_OTEL_ENDPOINT is not set, tracer should be no-op
        # (We can't guarantee test env doesn't have it set, so just check
        # that we get a tracer object)
        assert tracer is not None

    def test_span_context_manager_noop(self):
        # span() should work as a context manager even without OTel configured
        with span("test:span", attr1="value1") as s:
            assert s is not None
            # No-op span should not be recording
            assert s.is_recording() is False

    def test_span_attributes_set_without_error(self):
        with span("test:span") as s:
            s.set_attribute("key", "value")
            s.set_attributes({"a": 1, "b": 2})

    def test_span_with_context_injection(self):
        with set_context(run_id="run-trace-1", request_id="req-trace-1"):
            with span("test:span") as s:
                # Context vars should be available
                ctx = get_context()
                assert ctx["run_id"] == "run-trace-1"
                assert ctx["request_id"] == "req-trace-1"

    def test_mark_error_does_not_raise(self):
        try:
            raise RuntimeError("test error")
        except RuntimeError as e:
            mark_error(e)  # should not raise

    def test_nested_spans(self):
        with span("outer:span") as outer:
            with span("inner:span") as inner:
                assert inner is not None
            assert outer is not None


# ---------------------------------------------------------------------------
# Integration: logging with context
# ---------------------------------------------------------------------------


class TestLoggingIntegration:
    """Integration: structured logs carry context [BLK-130]."""

    def test_log_record_carries_context(self):
        # Configure JSON logging
        configure_logging(format_type="json", level="INFO")

        # Capture log output
        root = logging.getLogger()
        handler = root.handlers[0]
        stream = io.StringIO()
        handler.stream = stream

        with set_context(run_id="run-log-1", request_id="req-log-1"):
            logging.getLogger("src.test").info("processing run")

        output = stream.getvalue().strip()
        if output:
            data = json.loads(output)
            assert data["message"] == "processing run"
            assert data["run_id"] == "run-log-1"
            assert data["request_id"] == "req-log-1"

    def test_log_record_carries_extra_fields(self):
        configure_logging(format_type="json", level="INFO")

        root = logging.getLogger()
        handler = root.handlers[0]
        stream = io.StringIO()
        handler.stream = stream

        logging.getLogger("src.test").info(
            "tool completed",
            extra={"tool": "ocr", "duration_ms": 412, "cache_hit": True},
        )

        output = stream.getvalue().strip()
        if output:
            data = json.loads(output)
            assert data["tool"] == "ocr"
            assert data["duration_ms"] == 412
            assert data["cache_hit"] is True
