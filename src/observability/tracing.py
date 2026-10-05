"""OpenTelemetry tracing wrapper [BLK-130].

Provides a thin wrapper around OpenTelemetry that is:
- **Zero-overhead** when `ADE_OTEL_ENDPOINT` is not set (no-op)
- **Span hierarchy** matching: HTTP → run:execute → react:cycle → tool/llm/validate
- **Span attributes** for tokens, cost, cache hit, duration, confidence

When OTel is not configured, spans are no-op context managers that do
nothing — no imports of opentelemetry SDK, no overhead.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

from src.observability.context import get_context

logger = logging.getLogger(__name__)

# Check if OTel is configured
_OTEL_ENDPOINT = os.environ.get("ADE_OTEL_ENDPOINT", "")
_OTEL_ENABLED = bool(_OTEL_ENDPOINT)

# Lazily import OTel only if enabled
_tracer: Any = None
if _OTEL_ENABLED:
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource

        _resource = Resource.create({"service.name": "adep-backend"})
        _provider = TracerProvider(resource=_resource)
        _exporter = OTLPSpanExporter(endpoint=_OTEL_ENDPOINT)
        _processor = BatchSpanProcessor(_exporter)
        _provider.add_span_processor(_processor)
        trace.set_tracer_provider(_provider)
        _tracer = trace.get_tracer("adep")
        logger.info("OpenTelemetry tracing enabled, endpoint=%s", _OTEL_ENDPOINT)
    except ImportError:
        logger.warning(
            "ADE_OTEL_ENDPOINT set but opentelemetry packages not installed. "
            "Tracing will be no-op. Install with: pip install opentelemetry-sdk "
            "opentelemetry-exporter-otlp"
        )
        _OTEL_ENABLED = False


class _NoOpSpan:
    """No-op span when OTel is disabled."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_attributes(self, attrs: dict[str, Any]) -> None:
        pass

    def record_exception(self, exc: BaseException) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def end(self) -> None:
        pass

    def is_recording(self) -> bool:
        return False


class _NoOpTracer:
    """No-op tracer when OTel is disabled."""

    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        **kwargs: Any,
    ) -> Iterator[_NoOpSpan]:
        yield _NoOpSpan()


_tracer_instance: Any = _tracer if _OTEL_ENABLED and _tracer is not None else _NoOpTracer()


def get_tracer() -> Any:
    """Return the configured tracer (real or no-op)."""
    return _tracer_instance


@contextmanager
def span(
    name: str,
    **attributes: Any,
) -> Iterator[Any]:
    """Start a span with optional attributes [BLK-130].

    Automatically injects context variables (request_id, run_id, cycle)
    as span attributes. When OTel is disabled, this is a no-op.

    Usage::

        with span("tool:ocr", tool="ocr", provider="paddle", duration_ms=412):
            ...
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as s:
        # Inject context vars as span attributes
        ctx = get_context()
        for key, value in ctx.items():
            s.set_attribute(key, value)
        # Set caller-provided attributes
        for key, value in attributes.items():
            s.set_attribute(key, value)
        yield s


def mark_error(exc: BaseException) -> None:
    """Mark the current span as errored with exception details [BLK-130]."""
    if not _OTEL_ENABLED:
        return
    try:
        from opentelemetry import trace

        current = trace.get_current_span()
        current.record_exception(exc)
        from opentelemetry.trace import Status, StatusCode

        current.set_status(Status(StatusCode.ERROR, str(exc)))
    except Exception:
        pass
